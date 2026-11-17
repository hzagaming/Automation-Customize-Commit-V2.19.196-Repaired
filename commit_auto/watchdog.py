#!/usr/bin/env python3
"""看门狗：自动提交进程挂掉就按 auto.json 里的配置重新拉起。

    python3 -m commit_auto.watchdog
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import engine

STATE = engine.state_dir()
AUTO = STATE / "auto.json"
ROOT = Path(__file__).resolve().parent.parent


def heartbeat_age() -> float:
    path = STATE / "auto.hb"
    if not path.exists():
        return 1e9
    return time.time() - float(path.read_text(encoding="utf-8").strip() or 0)


def kill(pid: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except OSError:
            return
        time.sleep(0.5)


def read_config() -> dict | None:
    if not AUTO.exists():
        return None
    try:
        return json.loads(AUTO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def spawn(config: dict) -> dict:
    cmd = [sys.executable, "-m", "commit_auto.auto", "--repo", config["repo"],
           "--interval", f"{config.get('interval', 30):g}", "--push-every", "1"]
    mode = config.get("mode", "now")
    if mode == "pre2000":
        cmd += ["--date-from", "1970-01-01", "--date-to", "2000-01-01"]
    elif mode == "daily":
        cmd += ["--daily-start", "1970-01-01", "--daily-end", "2000-01-01"]
    with (STATE / "auto.out").open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log, stderr=log, start_new_session=True)
    config["pid"] = proc.pid
    config["restarted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    AUTO.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    print(f"{config['restarted_at']} 重启自动提交 pid={proc.pid} mode={mode}", flush=True)
    return config


def main() -> None:
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"看门狗启动，每 {interval:g} 秒检查一次：{AUTO}", flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        config = read_config()
        if config and config.get("pid"):
            limit = max(3 * float(config.get("interval", 30)), 60)
            if heartbeat_age() > limit:
                print(f"心跳超过 {limit:g} 秒，重启", flush=True)
                kill(config["pid"])
                (STATE / "auto.hb").write_text(str(time.time()), encoding="utf-8")
                spawn(config)
        time.sleep(interval)


if __name__ == "__main__":
    main()
