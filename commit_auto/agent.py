"""launchd agent so due jobs run even when the GUI is closed."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LABEL = "com.automation-customize-commit"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
ROOT = Path(__file__).resolve().parent.parent


def is_installed() -> bool:
    return PLIST.exists()


def plist_body() -> str:
    args = [sys.executable, "-m", "commit_auto.cli", "run"]
    argv = "".join(f"        <string>{a}</string>\n" for a in args)
    env = ""
    override = os.environ.get("COMMIT_AUTO_HOME")
    if override:
        env = ("    <key>EnvironmentVariables</key>\n    <dict>\n"
               f"        <key>COMMIT_AUTO_HOME</key><string>{override}</string>\n    </dict>\n")
    state = Path(override) if override else ROOT / ".state"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{argv}    </array>
    <key>WorkingDirectory</key><string>{ROOT}</string>
    <key>StartInterval</key><integer>60</integer>
    <key>RunAtLoad</key><true/>
{env}    <key>StandardOutPath</key><string>{state / 'agent.out'}</string>
    <key>StandardErrorPath</key><string>{state / 'agent.err'}</string>
</dict>
</plist>
"""


def install() -> Path:
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist_body(), encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    proc = subprocess.run(["launchctl", "load", str(PLIST)], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"launchctl load 失败: {proc.stderr.strip()}")
    return PLIST


def uninstall() -> None:
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    PLIST.unlink(missing_ok=True)
