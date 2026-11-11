# Automation Customize Commit · V2.19.196

按**你自己选的时间**自动执行 `git commit`，并按需推送到 GitHub。图形界面 + 命令行 + 后台守护代理，零第三方依赖（只用 Python 标准库和 git）。

## 它解决什么

平时想固定在某个时间点提交（每日构建记录、周报、定时快照），但那个时间人不在电脑前。这个工具让你提前登记「几点、在哪个仓库、提交什么」，到点由后台代理自己跑，关掉界面也不影响。

## 快速开始

```bash
./run.command                 # 打开图形界面
```

窗口中填：仓库路径 → 执行时间 → 提交信息 → 选择提交内容 → 添加任务。

首次使用点右上角 **安装后台代理**：它会写入一个 launchd 任务，每 60 秒检查一次到期任务。装一次即可，之后关掉浏览器也照常执行。

命令行等价用法：

```bash
python3 -m commit_auto.cli add --repo ~/code/proj --at "2026-11-12 09:30" -m "chore: nightly sync"
python3 -m commit_auto.cli list
python3 -m commit_auto.cli run          # 手动执行所有到期任务
python3 -m commit_auto.cli install      # 安装 launchd 代理
```

## 三种提交内容

| 模式 | 行为 |
| --- | --- |
| 追加时间戳到文件 | 往指定文件追加一行 `时间 提交信息`，只提交这个文件。默认 `commit-log.txt`，适合当每日打卡记录 |
| 提交仓库全部改动 | `git add -A` 后提交，把你手上未提交的改动一并交上去 |
| 空提交 | `git commit --allow-empty`，不改任何文件 |

## 两个时间开关

- **执行时间**：任务到点才跑，早于当前时间的任务会在下一次轮询立即执行。
- **commit 时间戳写成所选时间**（`--backdate`）：把 `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE` 设成你选的那个时间。适合补历史，但 push 后 GitHub 显示的提交时间就是这个回填值，不是真实执行时间。

## 失败重试

commit 或 push 失败会记 `error` 并累计次数，最多重试 5 次，每次轮询都会再试。日志见界面底部，文件在 `.state/run.log`。

## 目录结构

```
commit_auto/engine.py   任务存储、时间解析、git 执行
commit_auto/agent.py    launchd 守护代理安装/卸载
commit_auto/gui.py      本地 Web 界面（127.0.0.1，仅本机可访问）
commit_auto/cli.py      命令行
tests/test_engine.py    引擎单元测试（真实临时 git 仓库）
```

## 测试

```bash
python3 -m unittest discover -s tests
```

## 版本

当前 V2.19.196，版本号在 `VERSION` 文件，界面与 CLI `--version` 都从这里读。

## 说明

- 状态目录 `.state/` 默认在项目内，可用环境变量 `COMMIT_AUTO_HOME` 覆盖。
- 后台代理只在 macOS 上实现（launchd）。其他系统请用 cron 调用 `python3 -m commit_auto.cli run`。
- 回填时间戳会改变提交在 GitHub 上呈现的时间线，请只用于自己的仓库。
