"""DeepSeek API 客户端模块"""

from openai import OpenAI

from .config import Settings
from .notion_client import Task


SYSTEM_PROMPT = """你是一个专业的周报撰写助手。你的任务是根据用户提供的任务列表，生成一份简洁、专业、有条理的周报。

要求：
1. 周报应该简洁明了，突出重点工作内容
2. 按照工作类型或项目进行分类整理
3. 对于已完成的任务，突出成果
4. 对于进行中的任务，说明当前进度
5. 使用专业但易懂的语言
6. 输出格式为 Markdown，包含适当的标题和列表
7. 总字数控制在 300-500 字之间

输出格式示例：
## 本周工作总结

### 已完成工作
- 工作项1：简要描述成果
- 工作项2：简要描述成果

### 进行中工作
- 工作项1：当前进度说明
- 工作项2：当前进度说明

### 下周计划
- 基于进行中的工作，简要说明下周重点

---
*周报生成时间：{生成时间}*
"""


class DeepSeekService:
    """DeepSeek 服务类"""

    def __init__(self, settings: Settings):
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model

    def generate_weekly_report(self, tasks: list[Task], week_start: str, week_end: str) -> str:
        """根据任务列表生成周报"""
        if not tasks:
            return self._generate_empty_report(week_start, week_end)

        # 构建任务描述
        task_descriptions = self._format_tasks_for_prompt(tasks)

        user_prompt = f"""请根据以下本周（{week_start} 至 {week_end}）的任务列表生成周报：

{task_descriptions}

请生成一份专业的周报总结。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        return response.choices[0].message.content or ""

    def _format_tasks_for_prompt(self, tasks: list[Task]) -> str:
        """将任务列表格式化为提示词内容"""
        completed_tasks = [t for t in tasks if t.status == "已完成"]
        in_progress_tasks = [t for t in tasks if t.status == "进行中"]

        lines = []

        if completed_tasks:
            lines.append("【已完成的任务】")
            for task in completed_tasks:
                task_info = f"- {task.name}"
                if task.description:
                    task_info += f"（{task.description}）"
                if task.task_type:
                    task_info += f" [类型: {', '.join(task.task_type)}]"
                if task.priority:
                    task_info += f" [优先级: {task.priority}]"
                lines.append(task_info)
            lines.append("")

        if in_progress_tasks:
            lines.append("【进行中的任务】")
            for task in in_progress_tasks:
                task_info = f"- {task.name}"
                if task.description:
                    task_info += f"（{task.description}）"
                if task.task_type:
                    task_info += f" [类型: {', '.join(task.task_type)}]"
                if task.priority:
                    task_info += f" [优先级: {task.priority}]"
                if task.due_date:
                    task_info += f" [截止: {task.due_date}]"
                lines.append(task_info)

        return "\n".join(lines)

    def _generate_empty_report(self, week_start: str, week_end: str) -> str:
        """生成空周报（无任务时）"""
        return f"""## 本周工作总结

**周期：{week_start} 至 {week_end}**

本周暂无记录的任务更新。

---
*周报由系统自动生成*
"""

