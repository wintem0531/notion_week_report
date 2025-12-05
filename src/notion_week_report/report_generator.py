"""周报生成器模块"""

from datetime import datetime
from pathlib import Path

from .config import Settings, get_settings
from .notion_client import NotionService, Task
from .deepseek_client import DeepSeekService
from .github_client import GitHubService


def _count_all_tasks(tasks: list[Task]) -> tuple[int, int, int]:
    """递归统计所有任务数量（包括子任务）

    Returns:
        (总数, 已完成数, 进行中数)
    """
    total = 0
    completed = 0
    in_progress = 0

    for task in tasks:
        total += 1
        if task.status == "已完成":
            completed += 1
        elif task.status == "进行中":
            in_progress += 1

        # 递归统计子任务
        sub_total, sub_completed, sub_in_progress = _count_all_tasks(task.children)
        total += sub_total
        completed += sub_completed
        in_progress += sub_in_progress

    return total, completed, in_progress


def _print_task_tree(task: Task, indent: int = 0):
    """递归打印任务树"""
    prefix = "   " + "  " * indent
    status_emoji = "✅" if task.status == "已完成" else "🔄"

    # 打印任务名称
    if task.parent_task_name and indent == 0:
        print(f"{prefix}{status_emoji} [{task.parent_task_name}] {task.name} [{task.status}]")
    else:
        print(f"{prefix}{status_emoji} {task.name} [{task.status}]")

    # 打印 Git 仓库和提交信息
    if task.git_repo_url:
        git_prefix = prefix + "   "
        print(f"{git_prefix}🔗 Git: {task.git_repo_url}")
        if task.git_commits:
            print(f"{git_prefix}📝 本周 {len(task.git_commits)} 条提交:")
            for commit in task.git_commits[:5]:  # 预览最多显示 5 条
                msg = commit.message[:40] + "..." if len(commit.message) > 40 else commit.message
                print(f"{git_prefix}   · {commit.sha}: {msg}")
            if len(task.git_commits) > 5:
                print(f"{git_prefix}   ... 还有 {len(task.git_commits) - 5} 条提交")

    # 递归打印子任务
    for child in task.children:
        _print_task_tree(child, indent + 1)


class WeeklyReportGenerator:
    """周报生成器"""

    def __init__(
        self, settings: Settings | None = None, config_path: Path | None = None
    ):
        if settings is None:
            settings = get_settings(config_path)
        self.settings = settings
        self.notion_service = NotionService(self.settings)
        self.deepseek_service = DeepSeekService(self.settings)
        # 初始化 GitHub 服务（如果启用）
        self.github_service = None
        if self.settings.github_enabled:
            self.github_service = GitHubService(token=self.settings.github_token)

    def _fetch_git_commits_for_tasks(
        self,
        tasks: list[Task],
        week_start: datetime,
        week_end: datetime,
    ) -> None:
        """为任务列表获取 Git 提交历史（递归处理子任务）"""
        if not self.github_service:
            return

        for task in tasks:
            if task.git_repo_url:
                commits = self.github_service.get_weekly_commits(
                    repo_url=task.git_repo_url,
                    week_start=week_start,
                    week_end=week_end,
                )
                # 将 GitCommit 转换为 notion_client 中的 GitCommit 模型
                from .notion_client import GitCommit as TaskGitCommit

                task.git_commits = [
                    TaskGitCommit(
                        sha=c.sha,
                        message=c.message,
                        author=c.author,
                        date=c.date,
                        url=c.url,
                    )
                    for c in commits
                ]
                if commits:
                    print(f"   📦 {task.name}: 获取到 {len(commits)} 条提交")

            # 递归处理子任务
            if task.children:
                self._fetch_git_commits_for_tasks(task.children, week_start, week_end)

    def generate_and_publish(self) -> dict:
        """生成并发布周报"""
        print("🚀 开始生成周报...")

        # 1. 获取本周时间范围
        week_start, week_end = self.notion_service.get_week_range()
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        print(f"📅 周期：{week_start_str} 至 {week_end_str}")

        # 2. 获取本周任务（带层级）
        print("📋 正在获取本周任务...")
        tasks = self.notion_service.get_weekly_tasks()

        # 统计任务数量
        total_count, completed_count, in_progress_count = _count_all_tasks(tasks)
        print(f"   找到 {total_count} 个相关任务（{len(tasks)} 个顶级任务）")

        if tasks:
            print(f"   - 已完成: {completed_count} 个")
            print(f"   - 进行中: {in_progress_count} 个")

            # 3. 获取 Git 提交历史（如果启用）
            if self.github_service:
                print("\n🔍 正在获取 Git 提交历史...")
                self._fetch_git_commits_for_tasks(tasks, week_start, week_end)

            # 打印任务详情（带层级）
            print("\n📝 任务列表:")
            for task in tasks:
                _print_task_tree(task)

        # 4. 使用 DeepSeek 生成周报内容
        print("\n🤖 正在使用 DeepSeek 生成周报...")
        report_content = self.deepseek_service.generate_weekly_report(
            tasks=tasks,
            week_start=week_start_str,
            week_end=week_end_str,
        )
        print("   周报内容生成完成")

        # 5. 生成周报标题
        report_title = f"周报 {week_start_str} ~ {week_end_str}"

        # 6. 发布到 Notion
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
            "task_count": total_count,
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
