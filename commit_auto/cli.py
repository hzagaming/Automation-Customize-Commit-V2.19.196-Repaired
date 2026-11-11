"""Command line front end."""

from __future__ import annotations

import argparse

from . import agent, engine


def cmd_add(args) -> None:
    job = engine.add_job(args.repo, args.at, args.message, file=args.file,
                         branch=args.branch, push=not args.no_push, backdate=args.backdate)
    target = "并推送" if job["push"] else "仅本地"
    print(f"已登记 {job['id']}  {job['at']}  {job['repo']}  {target}")


def cmd_list(args) -> None:
    jobs = engine.load_jobs()
    if not jobs:
        print("暂无任务")
        return
    for job in sorted(jobs, key=lambda j: j["at"]):
        push = "push" if job["push"] else "local"
        print(f"{job['id']}  {job['at']}  {job['status']:<8} {push:<5} {job['repo']}  {job['message']}")


def cmd_rm(args) -> None:
    print("已删除" if engine.delete_job(args.id) else f"没有任务 {args.id}")


def cmd_run(args) -> None:
    due = engine.run_due(dry_run=args.dry_run)
    if not due:
        if args.verbose:
            print("没有到期任务")
        return
    for job in due:
        print(f"{job['id']}  {job['status']}  {job['repo']}  {job.get('last_error') or ''}")


def cmd_install(args) -> None:
    print(f"已安装后台代理: {agent.install()}")


def cmd_uninstall(args) -> None:
    agent.uninstall()
    print("已卸载后台代理")


def cmd_gui(args) -> None:
    from .gui import serve
    serve(port=args.port, open_browser=not args.no_browser)


def main() -> None:
    parser = argparse.ArgumentParser(prog="commit_auto", description="按你选的时间自动提交并推送")
    parser.add_argument("--version", action="version", version=f"Automation Customize Commit V{engine.VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="登记一个定时提交")
    add.add_argument("--repo", required=True)
    add.add_argument("--at", required=True, help='"2026-11-12 09:30" 或 "09:30"')
    add.add_argument("-m", "--message", default="chore: scheduled commit")
    add.add_argument("--file", help="追加一行时间戳到这个文件，而不是提交所有改动")
    add.add_argument("--branch", help="推送目标分支，默认当前分支")
    add.add_argument("--no-push", action="store_true", help="只提交，不推送到 origin")
    add.add_argument("--backdate", action="store_true", help="commit 时间戳写成 --at 的时间")
    add.set_defaults(func=cmd_add)

    sub.add_parser("list", help="查看任务").set_defaults(func=cmd_list)

    rm = sub.add_parser("rm", help="删除任务")
    rm.add_argument("id")
    rm.set_defaults(func=cmd_rm)

    run = sub.add_parser("run", help="执行所有到期任务")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("-v", "--verbose", action="store_true")
    run.set_defaults(func=cmd_run)

    sub.add_parser("install", help="安装 launchd 代理（每分钟检查）").set_defaults(func=cmd_install)
    sub.add_parser("uninstall", help="卸载 launchd 代理").set_defaults(func=cmd_uninstall)

    gui = sub.add_parser("gui", help="打开图形界面")
    gui.add_argument("--port", type=int, default=8765)
    gui.add_argument("--no-browser", action="store_true")
    gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
