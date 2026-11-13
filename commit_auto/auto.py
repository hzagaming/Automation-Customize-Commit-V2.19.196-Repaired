#!/usr/bin/env python3
"""全自动提交：每轮生成一个 sha256，追加到文件并提交。

    python3 -m commit_auto.auto --repo ~/code/proj --interval 300
"""

from __future__ import annotations

import argparse
import hashlib
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from . import engine

PID_FILE = engine.state_dir() / "auto.pid"


def push(repo: Path) -> None:
    for attempt in range(3):
        try:
            engine.git(repo, "push", "origin", "HEAD:main")
            return
        except RuntimeError as exc:
            print(f"push 失败 ({attempt + 1}/3): {exc}", flush=True)
            time.sleep(5 * (attempt + 1))
    print("push 连续失败，本轮跳过", flush=True)


def run(repo: Path, interval: float, count: int, push_every: int, log_file: str) -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    log_path = repo / log_file
    done = 0
    try:
        while count <= 0 or done < count:
            digest = hashlib.sha256(os.urandom(32)).hexdigest()
            stamp = datetime.now().isoformat(timespec="seconds")
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{digest} {stamp}\n")
            engine.git(repo, "add", "--", log_file)
            engine.git(repo, "commit", "-q", "-m", f"chore: {digest[:16]}")
            done += 1
            print(f"{stamp} #{done} {digest[:16]}", flush=True)
            if push_every and done % push_every == 0:
                push(repo)
            if count <= 0 or done < count:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\n已停止", flush=True)
    finally:
        PID_FILE.unlink(missing_ok=True)
        print(f"共提交 {done} 次", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="auto", description="每轮生成一个 sha256 并提交")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--interval", type=float, default=300, help="每轮间隔秒数")
    parser.add_argument("--count", type=int, default=0, help="总共提交多少次，0 = 无限")
    parser.add_argument("--push-every", type=int, default=1, help="每 N 轮推送一次，0 = 不推送")
    parser.add_argument("--log-file", default="hashes.log")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        sys.exit(f"{repo} 不是 git 仓库")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    run(repo, args.interval, args.count, args.push_every, args.log_file)


if __name__ == "__main__":
    main()
