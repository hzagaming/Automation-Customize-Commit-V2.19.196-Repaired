#!/usr/bin/env python3
"""按天回填提交：从起始日期到结束日期，每天一个提交，用 git fast-import 写入。

    python3 -m commit_auto.backfill --repo ~/code/proj --start 1970-01-01
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())


def identity(repo: Path) -> tuple[str, str]:
    def cfg(key: str) -> str:
        out = subprocess.run(["git", "config", key], cwd=repo, capture_output=True, text=True)
        return out.stdout.strip()

    name, email = cfg("user.name"), cfg("user.email")
    if not name or not email:
        sys.exit("仓库没有配置 user.name / user.email")
    return name, email


def stream(base: str, name: str, email: str, start: date, end: date, step: int, message: str,
           total: int | None = None):
    day = start
    first = True
    produced = 0
    while day <= end or (total and produced < total):
        if day > end:
            day = start
        ts = epoch(day)
        msg = f"{message} {day.isoformat()}\n".encode()
        head = f"author {name} <{email}> {ts} +0000\ncommitter {name} <{email}> {ts} +0000\n"
        from_line = f"from {base}\n" if first else ""
        yield f"commit refs/heads/main\nmark :{ts}\n{head}data {len(msg)}\n".encode() + msg + from_line.encode()
        first = False
        produced += 1
        if total and produced >= total:
            return
        day += timedelta(days=step)


def chunked_push(repo: Path, chunk: int = 50000) -> bool:
    """一次性推送被拒时，按 chunk 个提交分批推。"""
    print(f"整包推送失败，改按 {chunk} 条分批推送", flush=True)
    shas = subprocess.run(["git", "rev-list", "--first-parent", "--reverse", "HEAD"],
                          cwd=repo, capture_output=True, text=True).stdout.split()
    if not shas:
        return False
    remote = subprocess.run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=repo,
                            capture_output=True, text=True).stdout.split()
    start = shas.index(remote[0]) + 1 if remote and remote[0] in shas else 0
    points = shas[start + chunk - 1::chunk]
    if shas[-1] not in points:
        points.append(shas[-1])
    for sha in points:
        for attempt in range(3):
            push = subprocess.run(["git", "push", "origin", f"{sha}:main"], cwd=repo,
                                  capture_output=True, text=True)
            if push.returncode == 0:
                break
            time.sleep(5 * (attempt + 1))
        else:
            print(f"分批推送在 {sha[:8]} 处失败", flush=True)
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(prog="backfill")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--start", default="1970-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--step", type=int, default=1, help="每隔几天提交一次")
    parser.add_argument("--message", default="chore: backfill")
    parser.add_argument("--total", type=int, help="总共生成多少个提交（循环日期区间）")
    parser.add_argument("--loop", action="store_true", help="跑完一轮后从起始日期重新开始，永不停")
    parser.add_argument("--pause", type=int, default=300, help="两轮之间的间隔秒数")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        sys.exit(f"{repo} 不是 git 仓库")
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end:
        sys.exit("起始日期晚于结束日期")
    if epoch(start) < 0:
        sys.exit("Git 不接受 1970-01-01 之前的正常时间戳")

    name, email = identity(repo)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                          text=True).stdout.strip()
    total = len(range(0, (end - start).days + 1, args.step))
    print(f"回填 {start} → {end}：{total} 个提交，基于 {base[:7]}，作者 {name} <{email}>", flush=True)
    if args.dry_run:
        return

    round_no = 0
    while True:
        round_no += 1
        ok = False
        for attempt in range(5):
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                                  text=True).stdout.strip()
            proc = subprocess.Popen(["git", "fast-import", "--quiet"], cwd=repo, stdin=subprocess.PIPE)
            try:
                for chunk in stream(base, name, email, start, end, args.step, args.message, args.total):
                    proc.stdin.write(chunk)
                proc.stdin.close()
                ok = proc.wait() == 0
            except BrokenPipeError:
                ok = False
            if ok:
                break
            print(f"导入被并发提交打断 ({attempt + 1}/5)，1 秒后重试", flush=True)
            time.sleep(1)
        if not ok:
            print("连续 5 次导入失败，本轮跳过", flush=True)
            if not args.loop:
                sys.exit(1)
            time.sleep(args.pause)
            continue

        pushed = False
        for attempt in range(5):
            push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=repo, capture_output=True, text=True)
            if push.returncode == 0:
                pushed = True
                break
            print(f"push 失败 ({attempt + 1}/5): {push.stderr.strip()[:120]}", flush=True)
            time.sleep(5 * (attempt + 1))
        if not pushed:
            pushed = chunked_push(repo)

        total = len(range(0, (end - start).days + 1, args.step))
        count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo, capture_output=True,
                               text=True).stdout.strip()
        head = subprocess.run(["git", "log", "-1", "--format=%h %ai"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
        state = "" if pushed else "（推送未成功）"
        print(f"{datetime.now():%H:%M:%S} 第 {round_no} 轮完成{state}：本轮 {total} 个提交，仓库共 {count} 个，HEAD={head}", flush=True)
        if not args.loop or args.total:
            return
        time.sleep(args.pause)


if __name__ == "__main__":
    main()
