"""周报生成器模块"""

from pathlib import Path

from .config import Settings, get_settings
from .notion_client import NotionService
from .deepseek_client import DeepSeekService


class WeeklyReportGenerator:
    """周报生成器"""

    def __init__(self, settings: Settings | None = None, config_path: Path | None = None):
        if settings is None:
            settings = get_settings(config_path)
        self.settings = settings
        self.notion_service = NotionService(self.settings)
        self.deepseek_service = DeepSeekService(self.settings)

    def generate_and_publish(self) -> dict:
        """生成并发布周报"""
        print("🚀 开始生成周报...")

        # 1. 获取本周时间范围
        week_start, week_end = self.notion_service.get_week_range()
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        print(f"📅 周期：{week_start_str} 至 {week_end_str}")

        # 2. 获取本周任务
        print("📋 正在获取本周任务...")
        tasks = self.notion_service.get_weekly_tasks()
        print(f"   找到 {len(tasks)} 个相关任务")

        if tasks:
            completed_count = sum(1 for t in tasks if t.status == "已完成")
            in_progress_count = sum(1 for t in tasks if t.status == "进行中")
            print(f"   - 已完成: {completed_count} 个")
            print(f"   - 进行中: {in_progress_count} 个")

            # 打印任务详情
            print("\n📝 任务列表:")
            for task in tasks:
                status_emoji = "✅" if task.status == "已完成" else "🔄"
                print(f"   {status_emoji} {task.name} [{task.status}]")

        # 3. 使用 DeepSeek 生成周报内容
        print("\n🤖 正在使用 DeepSeek 生成周报...")
        report_content = self.deepseek_service.generate_weekly_report(
            tasks=tasks,
            week_start=week_start_str,
            week_end=week_end_str,
        )
        print("   周报内容生成完成")

        # 4. 生成周报标题
        report_title = f"周报 {week_start_str} ~ {week_end_str}"

        # 5. 发布到 Notion
        print("\n📤 正在发布到 Notion...")
        result = self.notion_service.create_weekly_report(
            title=report_title,
            content=report_content,
            start_date=week_start,
            end_date=week_end,
        )
        print("   ✅ 周报已发布!")
        print(f"   📎 链接: https://notion.so/{result['id'].replace('-', '')}")

        return {
            "success": True,
            "title": report_title,
            "page_id": result["id"],
            "url": f"https://notion.so/{result['id'].replace('-', '')}",
            "task_count": len(tasks),
            "content": report_content,
        }


def run_report_generation(config_path: Path | None = None) -> dict:
    """运行周报生成（供外部调用）"""
    generator = WeeklyReportGenerator(config_path=config_path)
    return generator.generate_and_publish()


if __name__ == "__main__":
    # 直接运行此模块时，手动触发生成
    result = run_report_generation()
    print("\n" + "=" * 50)
    print("生成结果:")
    print(f"  标题: {result['title']}")
    print(f"  任务数: {result['task_count']}")
    print(f"  链接: {result['url']}")
