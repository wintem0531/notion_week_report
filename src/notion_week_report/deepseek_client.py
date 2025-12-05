"""DeepSeek API 客户端模块"""

from openai import OpenAI

from .config import Settings
from .notion_client import Task


class DeepSeekService:
    """DeepSeek 服务类"""

    def __init__(self, settings: Settings):
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model
        self.system_prompt = settings.system_prompt
        self.user_prompt_template = settings.user_prompt_template
        self.temperature = settings.prompt_temperature
        self.max_tokens = settings.prompt_max_tokens

    def generate_weekly_report(
        self, tasks: list[Task], week_start: str, week_end: str
    ) -> str:
        """根据任务列表生成周报"""
        if not tasks:
            return self._generate_empty_report(week_start, week_end)

        # 构建任务描述（支持层级）
        task_descriptions = self._format_tasks_for_prompt(tasks)

        # 使用配置的用户提示词模板
        user_prompt = self.user_prompt_template.format(
            week_start=week_start,
            week_end=week_end,
            task_descriptions=task_descriptions,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response.choices[0].message.content or ""

    def _format_tasks_for_prompt(self, tasks: list[Task]) -> str:
        """将任务列表格式化为提示词内容（支持层级结构）"""
        # 分离已完成和进行中的任务
        completed_tasks = [t for t in tasks if t.status == "已完成"]
        in_progress_tasks = [t for t in tasks if t.status == "进行中"]

        lines = []

        if completed_tasks:
            lines.append("【已完成的任务】")
            lines.extend(self._format_task_group(completed_tasks))
            lines.append("")

        if in_progress_tasks:
            lines.append("【进行中的任务】")
            lines.extend(self._format_task_group(in_progress_tasks))

        return "\n".join(lines)

    def _format_task_group(self, tasks: list[Task], indent: int = 0) -> list[str]:
        """格式化任务组（递归处理子任务，包含 Git 提交信息）"""
        lines = []
        prefix = "  " * indent

        for task in tasks:
            # 构建任务基本信息
            task_info = f"{prefix}- {task.name}"

            # 如果有父任务名称（说明是子任务但父任务不在本组中），添加上下文
            if task.parent_task_name and indent == 0:
                task_info = f"{prefix}- [{task.parent_task_name}] {task.name}"

            # 添加描述
            if task.description:
                task_info += f"（{task.description}）"

            # 添加元信息
            meta_parts = []
            if task.task_type:
                meta_parts.append(f"类型: {', '.join(task.task_type)}")
            if task.priority:
                meta_parts.append(f"优先级: {task.priority}")
            if task.due_date:
                meta_parts.append(f"截止: {task.due_date}")

            if meta_parts:
                task_info += f" [{'; '.join(meta_parts)}]"

            lines.append(task_info)

            # 添加 Git 提交信息（如果有）
            if task.git_commits:
                commit_prefix = "  " * (indent + 1)
                lines.append(f"{commit_prefix}[本周 Git 提交记录]:")
                for commit in task.git_commits[:10]:  # 最多显示 10 条
                    # 截断过长的提交信息
                    msg = (
                        commit.message[:60] + "..."
                        if len(commit.message) > 60
                        else commit.message
                    )
                    lines.append(f"{commit_prefix}  · {commit.sha}: {msg}")

            # 递归处理子任务
            if task.children:
                # 分离子任务的状态
                completed_children = [c for c in task.children if c.status == "已完成"]
                in_progress_children = [
                    c for c in task.children if c.status == "进行中"
                ]

                # 根据当前任务组的状态决定显示哪些子任务
                # 已完成的父任务显示所有子任务
                # 进行中的父任务也显示所有子任务
                all_children = completed_children + in_progress_children
                if all_children:
                    lines.extend(self._format_task_group(all_children, indent + 1))

        return lines

    def _generate_empty_report(self, week_start: str, week_end: str) -> str:
        """生成空周报（无任务时）"""
        return f"""## 本周工作总结

**周期：{week_start} 至 {week_end}**

本周暂无记录的任务更新。

---
*周报由系统自动生成*
"""
