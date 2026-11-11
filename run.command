#!/bin/bash
# 双击启动图形界面
cd "$(dirname "$0")" || exit 1
exec python3 -m commit_auto.cli gui "$@"
