"""
自动修复系统入口

用法:
  python -m autoheal start          # 启动（前台）
  python -m autoheal start --bg     # 启动（后台）
  python -m autoheal butler         # 管家模式：一键启动容器+监控+自动修复
  python -m autoheal butler --down  # 停止所有容器
  python -m autoheal status         # 查看状态
  python -m autoheal report         # 生成报告
  python -m autoheal config         # 查看配置
"""

import argparse
import asyncio
import sys
import signal
import logging

from .agent import AutoHealAgent, Butler
from .dashboard import Dashboard, print_dashboard
from .config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("autoheal")


def cmd_start(args):
    """启动监控"""
    agent = AutoHealAgent()

    def handle_signal(sig, frame):
        logger.info("收到停止信号")
        agent.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    asyncio.run(agent.start())


def cmd_status(args):
    """查看状态"""
    dashboard = Dashboard()
    print_dashboard(dashboard)


def cmd_report(args):
    """生成报告"""
    dashboard = Dashboard()
    hours = getattr(args, "hours", 24)
    report = dashboard.get_report(hours=hours)

    print(f"\n=== AutoHeal 修复报告 (最近 {hours} 小时) ===")
    print(f"总修复次数: {report['total_repairs']}")
    print(f"成功: {report['successful']}")
    print(f"失败: {report['failed']}")

    if report["by_type"]:
        print("\n按错误类型:")
        for error_type, stats in report["by_type"].items():
            print(f"  {error_type}: {stats['total']} 次 "
                  f"(成功 {stats['success']}, 失败 {stats['failed']})")
    print()


def cmd_config(args):
    """查看配置"""
    config = get_config()
    print("\n=== AutoHeal 配置 ===")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    print()


def cmd_butler(args):
    """管家模式"""
    butler = Butler()

    if getattr(args, "down", False):
        asyncio.run(butler.stop())
        return

    def handle_signal(sig, frame):
        logger.info("收到停止信号")
        butler.agent.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    asyncio.run(butler.start())


def main():
    parser = argparse.ArgumentParser(
        prog="autoheal",
        description="Inner Mirror 自动修复系统",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # start
    start_parser = subparsers.add_parser("start", help="启动监控")
    start_parser.set_defaults(func=cmd_start)

    # butler
    butler_parser = subparsers.add_parser("butler", help="管家模式")
    butler_parser.add_argument("--down", action="store_true", help="停止所有容器")
    butler_parser.set_defaults(func=cmd_butler)

    # status
    status_parser = subparsers.add_parser("status", help="查看状态")
    status_parser.set_defaults(func=cmd_status)

    # report
    report_parser = subparsers.add_parser("report", help="生成报告")
    report_parser.add_argument("--hours", type=int, default=24, help="报告时间范围（小时）")
    report_parser.set_defaults(func=cmd_report)

    # config
    config_parser = subparsers.add_parser("config", help="查看配置")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
