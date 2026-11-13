"""Scheduled-commit engine: job store, time parsing, git execution."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
MAX_ATTEMPTS = 5
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%H:%M")
REPEAT_DELTAS = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def state_dir() -> Path:
    override = os.environ.get("COMMIT_AUTO_HOME")
    path = Path(override) if override else ROOT / ".state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_at(text: str) -> datetime:
    for fmt in TIME_FORMATS:
        try:
            moment = datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
        if fmt == "%H:%M":
            now = datetime.now()
            moment = now.replace(hour=moment.hour, minute=moment.minute, second=0, microsecond=0)
            if moment <= now:
                moment += timedelta(days=1)
        return moment
    raise ValueError(f"无法识别的时间: {text!r}")


def log(message: str) -> None:
    with (state_dir() / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")


def tail_log(lines: int = 40) -> list[str]:
    path = state_dir() / "run.log"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()[-lines:]


def load_jobs() -> list[dict]:
    path = state_dir() / "jobs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_jobs(jobs: list[dict]) -> None:
    path = state_dir() / "jobs.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def add_job(repo: str, at: str, message: str = "chore: scheduled commit", *,
            file: str | None = None, branch: str | None = None,
            push: bool = True, backdate: bool = False, repeat: str = "none",
            raw_date: str | None = None) -> dict:
    path = Path(repo).expanduser().resolve()
    if not (path / ".git").exists():
        raise ValueError(f"{path} 不是 git 仓库")
    if repeat not in {"none", *REPEAT_DELTAS}:
        raise ValueError(f"不支持的重复方式: {repeat}")
    when = datetime.now() if raw_date else parse_at(at)
    job = {
        "id": uuid.uuid4().hex[:8],
        "repo": str(path),
        "at": when.isoformat(timespec="minutes"),
        "message": message,
        "file": file or None,
        "branch": branch or None,
        "push": bool(push),
        "backdate": bool(backdate or raw_date),
        "raw_date": raw_date,
        "repeat": repeat,
        "status": "pending",
        "attempts": 0,
        "last_error": None,
        "last_run": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    return job


def delete_job(job_id: str) -> bool:
    jobs = load_jobs()
    keep = [j for j in jobs if j["id"] != job_id]
    if len(keep) == len(jobs):
        return False
    save_jobs(keep)
    return True


def git(repo: Path, *args: str, env: dict | None = None) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip().splitlines()[-1] or "git 执行失败")
    return proc.stdout.strip()


def execute(job: dict, now: datetime | None = None) -> None:
    repo = Path(job["repo"])
    now = now or datetime.now()
    stamp = job["at"] if job["backdate"] else now.isoformat(timespec="seconds")

    if job["file"]:
        target = repo / job["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {job['message']}\n")
        git(repo, "add", "--", job["file"])
    else:
        git(repo, "add", "-A")

    env = {}
    if job.get("raw_date"):
        env = {"GIT_AUTHOR_DATE": job["raw_date"], "GIT_COMMITTER_DATE": job["raw_date"]}
    elif job["backdate"]:
        env = {"GIT_AUTHOR_DATE": job["at"], "GIT_COMMITTER_DATE": job["at"]}

    if git(repo, "diff", "--cached", "--name-only"):
        git(repo, "commit", "-m", job["message"], env=env)
    else:
        git(repo, "commit", "--allow-empty", "-m", job["message"], env=env)

    if job["push"]:
        branch = job["branch"] or git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        git(repo, "push", "origin", f"HEAD:{branch}")


def _reschedule(job: dict, now: datetime | None = None) -> None:
    step = REPEAT_DELTAS.get(job.get("repeat") or "none")
    if not step:
        return
    nxt = datetime.fromisoformat(job["at"]) + step
    now = now or datetime.now()
    while nxt <= now:
        nxt += step
    job.update(status="pending", at=nxt.isoformat(timespec="minutes"), attempts=0)


def _attempt(job: dict, now: datetime | None = None) -> bool:
    try:
        execute(job, now)
    except Exception as exc:  # noqa: BLE001 - surfaced to UI, retried next tick
        job.update(status="error", attempts=job["attempts"] + 1, last_error=str(exc))
        log(f"ERROR {job['id']} {job['repo']} {exc}")
        return False
    job.update(status="done", attempts=job["attempts"] + 1, last_error=None,
               last_run=datetime.now().isoformat(timespec="seconds"))
    log(f"OK {job['id']} {job['repo']} {job['message']} push={job['push']}")
    _reschedule(job)
    return True


def run_due(dry_run: bool = False) -> list[dict]:
    jobs = load_jobs()
    now = datetime.now()
    due = [j for j in jobs
           if j["status"] in {"pending", "error"}
           and j["attempts"] < MAX_ATTEMPTS
           and datetime.fromisoformat(j["at"]) <= now]
    for job in sorted(due, key=lambda j: j["at"]):
        if dry_run:
            job["result"] = "would-run"
            continue
        _attempt(job, now)
    if due and not dry_run:
        save_jobs(jobs)
    return due


def run_job(job_id: str) -> dict:
    """Run one job immediately, whatever its scheduled time."""
    jobs = load_jobs()
    for job in jobs:
        if job["id"] != job_id:
            continue
        _attempt(job)
        save_jobs(jobs)
        return job
    raise KeyError(f"没有任务 {job_id}")


def set_repeat(job_id: str, repeat: str) -> dict:
    if repeat not in {"none", *REPEAT_DELTAS}:
        raise ValueError(f"不支持的重复方式: {repeat}")
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            job["repeat"] = repeat
            save_jobs(jobs)
            return job
    raise KeyError(f"没有任务 {job_id}")


def commit_days(repo: str, days: int = 371) -> dict[str, int]:
    """每个自然日的提交数，用于热力图。"""
    path = Path(repo).expanduser().resolve()
    if not (path / ".git").exists():
        raise ValueError(f"{path} 不是 git 仓库")
    out = git(path, "log", f"--since={days} days ago", "--format=%ad", "--date=short")
    counts: dict[str, int] = {}
    for line in out.splitlines():
        if line.strip():
            counts[line.strip()] = counts.get(line.strip(), 0) + 1
    return counts


def next_due(jobs: list[dict]) -> dict | None:
    pending = [j for j in jobs if j["status"] in {"pending", "error"}
               and j["attempts"] < MAX_ATTEMPTS]
    return min(pending, key=lambda j: j["at"]) if pending else None
