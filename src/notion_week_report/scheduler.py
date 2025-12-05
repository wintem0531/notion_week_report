"""定时任务调度器模块"""

import time
from datetime import datetime
from pathlib import Path

import schedule

from .config import Settings, get_settings
from .report_generator import run_report_generation


class ReportScheduler:
    """周报定时调度器"""

    def __init__(
        self, settings: Settings | None = None, config_path: Path | None = None
    ):
        if settings is None:
            settings = get_settings(config_path)
        self.settings = settings
        self.config_path = config_path
        self._setup_schedule()

    def _setup_schedule(self):
        """设置定时任务"""
        day = self.settings.schedule_day.lower()
        time_str = self.settings.schedule_time

        # 根据配置的日期设置定时任务
        day_methods = {
            "monday": schedule.every().monday,
            "tuesday": schedule.every().tuesday,
            "wednesday": schedule.every().wednesday,
            "thursday": schedule.every().thursday,
            "friday": schedule.every().friday,
            "saturday": schedule.every().saturday,
            "sunday": schedule.every().sunday,
        }

        if day not in day_methods:
            raise ValueError(f"无效的日期配置: {day}")

        # 设置定时任务
        day_methods[day].at(time_str).do(self._run_job)

        print("📅 定时任务已配置:")
        print(f"   执行日期: {day.capitalize()}")
        print(f"   执行时间: {time_str}")

    def _run_job(self):
        """执行周报生成任务"""
        print(f"\n{'=' * 50}")
        print(f"⏰ 定时任务触发 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

        try:
            result = run_report_generation(self.config_path)
            print("\n✅ 周报生成成功!")
            print(f"   链接: {result['url']}")
        except Exception as e:
            print(f"\n❌ 周报生成失败: {e}")
            raise

    def run(self):
        """启动调度器"""
        print("\n🚀 周报调度器已启动")
        print("   按 Ctrl+C 停止\n")

        # 显示下次执行时间
        next_run = schedule.next_run()
        if next_run:
            print(f"⏳ 下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            print("\n\n👋 调度器已停止")


def start_scheduler(config_path: Path | None = None):
    """启动调度器（供外部调用）"""
    scheduler = ReportScheduler(config_path=config_path)
    scheduler.run()


if __name__ == "__main__":
    start_scheduler()
