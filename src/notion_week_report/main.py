"""周报生成工具主入口"""

import argparse
import sys
from pathlib import Path

from .notion_client import Task


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="自动周报生成工具 - 从 Notion 任务跟踪器自动生成周报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 手动触发生成周报
  uv run python -m notion_week_report.main --run

  # 使用指定配置文件
  uv run python -m notion_week_report.main --run --config /path/to/config.yaml

  # 启动定时任务调度器
  uv run python -m notion_week_report.main --schedule

  # 预览本周任务（不生成周报）
  uv run python -m notion_week_report.main --preview
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="配置文件路径 (默认: config.yaml)",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--run",
        "-r",
        action="store_true",
        help="立即运行，手动触发生成周报",
    )
    group.add_argument(
        "--schedule",
        "-s",
        action="store_true",
        help="启动定时任务调度器",
    )
    group.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="预览本周任务（不生成周报）",
    )

    args = parser.parse_args()

    # 转换配置路径
    config_path = Path(args.config) if args.config else None

    try:
        if args.run:
            run_now(config_path)
        elif args.schedule:
            run_scheduler(config_path)
        elif args.preview:
            preview_tasks(config_path)
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"\n❌ 配置文件错误: {e}")
        print("\n💡 提示: 请复制 config.example.yaml 为 config.yaml 并填入你的配置")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


def run_now(config_path: Path | None = None):
    """立即生成周报"""
    from .report_generator import run_report_generation

    print("=" * 50)
    print("📝 手动触发周报生成")
    print("=" * 50 + "\n")

    result = run_report_generation(config_path)

    print("\n" + "=" * 50)
    print("✅ 周报生成完成!")
    print("=" * 50)
    print(f"\n📌 标题: {result['title']}")
    print(f"📊 任务数: {result['task_count']}")
    print(f"🔗 链接: {result['url']}")
    print("\n📄 周报内容预览:")
    print("-" * 50)
    print(result["content"])


def run_scheduler(config_path: Path | None = None):
    """启动定时调度器"""
    from .scheduler import start_scheduler

    print("=" * 50)
    print("📅 启动周报定时调度器")
    print("=" * 50 + "\n")

    start_scheduler(config_path)


def _print_task_tree(task: Task, indent: int = 0):
    """递归打印任务树"""
    prefix = "   " + "  " * indent
    status_emoji = "✅" if task.status == "已完成" else "🔄"

    # 打印任务名称
    if task.parent_task_name and indent == 0:
        print(f"{prefix}{status_emoji} [{task.parent_task_name}] {task.name}")
    else:
        print(f"{prefix}{status_emoji} {task.name}")

    # 打印任务详情
    detail_prefix = prefix + "   "
    if task.description:
        print(f"{detail_prefix}描述: {task.description}")
    if task.task_type:
        print(f"{detail_prefix}类型: {', '.join(task.task_type)}")
    if task.due_date:
        print(f"{detail_prefix}截止: {task.due_date}")

    # 递归打印子任务
    for child in task.children:
        _print_task_tree(child, indent + 1)


def _count_all_tasks(tasks: list[Task]) -> int:
    """递归统计所有任务数量（包括子任务）"""
    count = len(tasks)
    for task in tasks:
        count += _count_all_tasks(task.children)
    return count


def preview_tasks(config_path: Path | None = None):
    """预览本周任务"""
    from .config import get_settings
    from .notion_client import NotionService

    print("=" * 50)
    print("👀 预览本周任务")
    print("=" * 50 + "\n")

    settings = get_settings(config_path)
    notion_service = NotionService(settings)

    week_start, week_end = notion_service.get_week_range()
    print(
        f"📅 周期: {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}\n"
    )

    # 获取层级结构的任务
    tasks = notion_service.get_weekly_tasks()

    if not tasks:
        print("📭 本周暂无相关任务记录")
        return

    total_count = _count_all_tasks(tasks)
    print(f"📋 找到 {total_count} 个任务（{len(tasks)} 个顶级任务）:\n")

    # 按状态分组显示
    completed = [t for t in tasks if t.status == "已完成"]
    in_progress = [t for t in tasks if t.status == "进行中"]

    if completed:
        print("✅ 已完成:")
        for task in completed:
            _print_task_tree(task)
            print()

    if in_progress:
        print("🔄 进行中:")
        for task in in_progress:
            _print_task_tree(task)
            print()


if __name__ == "__main__":
    main()
