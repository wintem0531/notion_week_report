"""Notion API 客户端模块"""

from datetime import datetime, timedelta
from typing import Any

from notion_client import Client
from pydantic import BaseModel, Field

from .config import Settings


class GitCommit(BaseModel):
    """Git 提交数据模型（从 github_client 导入时使用）"""

    sha: str = Field(description="提交 SHA")
    message: str = Field(description="提交信息")
    author: str = Field(description="提交作者")
    date: str = Field(description="提交日期")
    url: str = Field(description="提交链接")


class Task(BaseModel):
    """任务数据模型"""

    id: str
    name: str
    status: str
    description: str | None = None
    task_type: list[str] = []
    priority: str | None = None
    workload: str | None = None
    due_date: str | None = None
    last_edited_time: str | None = None
    # 父任务相关（通过 relation 属性）
    parent_task_ids: list[str] = Field(default_factory=list)
    parent_task_name: str | None = None
    # 子任务相关（通过 relation 属性）
    sub_task_ids: list[str] = Field(default_factory=list)
    # 子任务列表（构建层级时填充）
    children: list["Task"] = Field(default_factory=list)
    # Git 仓库相关
    git_repo_url: str | None = None
    git_commits: list[GitCommit] = Field(default_factory=list)


class NotionService:
    """Notion 服务类"""

    def __init__(self, settings: Settings):
        self.client = Client(auth=settings.notion_token)
        self.task_tracker_db_id = settings.task_tracker_database_id
        self.weekly_report_db_id = settings.weekly_report_database_id
        self.include_in_progress = settings.include_in_progress
        self.include_completed = settings.include_completed

    def get_week_range(self) -> tuple[datetime, datetime]:
        """获取本周的时间范围（周一到周日）"""
        today = datetime.now()
        # 计算本周一
        monday = today - timedelta(days=today.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        # 计算本周日
        sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return monday, sunday

    def _extract_relation_ids(self, relation_prop: dict[str, Any]) -> list[str]:
        """从关系属性中提取相关页面 ID"""
        if relation_prop.get("type") != "relation":
            return []

        relation_list = relation_prop.get("relation", [])
        return [item.get("id", "") for item in relation_list if item.get("id")]

    def _extract_task_from_page(self, page: dict[str, Any]) -> Task:
        """从 Notion 页面数据中提取任务信息"""
        properties = page.get("properties", {})

        # 提取任务名称
        name_prop = properties.get("任务名称", {})
        name = ""
        if name_prop.get("type") == "title":
            title_list = name_prop.get("title", [])
            name = "".join(t.get("plain_text", "") for t in title_list)

        # 提取状态
        status_prop = properties.get("状态", {})
        status = ""
        if status_prop.get("type") == "status":
            status_obj = status_prop.get("status")
            if status_obj:
                status = status_obj.get("name", "")

        # 提取描述
        desc_prop = properties.get("描述", {})
        description = None
        if desc_prop.get("type") == "rich_text":
            rich_text_list = desc_prop.get("rich_text", [])
            description = (
                "".join(t.get("plain_text", "") for t in rich_text_list) or None
            )

        # 提取任务类型
        type_prop = properties.get("任务类型", {})
        task_type = []
        if type_prop.get("type") == "multi_select":
            task_type = [
                opt.get("name", "") for opt in type_prop.get("multi_select", [])
            ]

        # 提取优先级
        priority_prop = properties.get("优先级", {})
        priority = None
        if priority_prop.get("type") == "select":
            select_obj = priority_prop.get("select")
            if select_obj:
                priority = select_obj.get("name")

        # 提取工作量等级
        workload_prop = properties.get("工作量等级", {})
        workload = None
        if workload_prop.get("type") == "select":
            select_obj = workload_prop.get("select")
            if select_obj:
                workload = select_obj.get("name")

        # 提取截止日期
        due_prop = properties.get("截止日期", {})
        due_date = None
        if due_prop.get("type") == "date":
            date_obj = due_prop.get("date")
            if date_obj:
                due_date = date_obj.get("start")

        # 提取更新时间
        last_edited = properties.get("更新时间：", {})
        last_edited_time = None
        if last_edited.get("type") == "last_edited_time":
            last_edited_time = last_edited.get("last_edited_time")

        # 提取父任务 ID（通过 "上级 任务" 关系属性）
        parent_prop = properties.get("上级 任务", {})
        parent_task_ids = self._extract_relation_ids(parent_prop)

        # 提取子任务 ID（通过 "子级 任务" 关系属性）
        sub_prop = properties.get("子级 任务", {})
        sub_task_ids = self._extract_relation_ids(sub_prop)

        # 提取 Git 仓库 URL
        git_prop = properties.get("Git仓库", {})
        git_repo_url = None
        if git_prop.get("type") == "url":
            git_repo_url = git_prop.get("url")

        return Task(
            id=page.get("id", ""),
            name=name,
            status=status,
            description=description,
            task_type=task_type,
            priority=priority,
            workload=workload,
            due_date=due_date,
            last_edited_time=last_edited_time,
            parent_task_ids=parent_task_ids,
            sub_task_ids=sub_task_ids,
            git_repo_url=git_repo_url,
        )

    def _get_page_title(self, page_id: str) -> str | None:
        """获取页面标题"""
        try:
            page = self.client.pages.retrieve(page_id=page_id)
            properties = page.get("properties", {})

            # 尝试多种可能的标题属性名
            for title_key in ["任务名称", "Name", "title", "名称"]:
                title_prop = properties.get(title_key, {})
                if title_prop.get("type") == "title":
                    title_list = title_prop.get("title", [])
                    return "".join(t.get("plain_text", "") for t in title_list)

            return None
        except Exception:
            return None

    def _build_task_hierarchy(self, tasks: list[Task]) -> list[Task]:
        """构建任务层级关系（基于 relation 属性）

        返回顶级任务列表（没有父任务或父任务不在本周任务中的任务）
        子任务会被挂载到对应的父任务下
        """
        # 创建任务 ID 到任务的映射
        task_map: dict[str, Task] = {task.id: task for task in tasks}

        # 第一步：填充父任务名称
        for task in tasks:
            if task.parent_task_ids:
                parent_id = task.parent_task_ids[0]  # 取第一个父任务
                if parent_id in task_map:
                    task.parent_task_name = task_map[parent_id].name
                else:
                    # 父任务不在本周列表中，尝试获取名称
                    task.parent_task_name = self._get_page_title(parent_id)

        # 第二步：构建子任务关系
        for task in tasks:
            # 将子任务添加到对应的父任务 children 中
            for sub_id in task.sub_task_ids:
                if sub_id in task_map:
                    child_task = task_map[sub_id]
                    if child_task not in task.children:
                        task.children.append(child_task)

        # 第三步：找出顶级任务（没有父任务在列表中的任务）
        root_tasks: list[Task] = []
        child_ids: set[str] = set()

        # 收集所有被标记为子任务的 ID
        for task in tasks:
            for sub_id in task.sub_task_ids:
                if sub_id in task_map:
                    child_ids.add(sub_id)

        # 顶级任务：不在任何任务的子任务列表中
        for task in tasks:
            if task.id not in child_ids:
                root_tasks.append(task)

        return root_tasks

    def get_weekly_tasks(self) -> list[Task]:
        """获取本周的任务列表（包含层级关系）"""
        monday, sunday = self.get_week_range()

        # 构建状态过滤条件
        status_filters = []
        if self.include_in_progress:
            status_filters.append(
                {
                    "property": "状态",
                    "status": {"equals": "进行中"},
                }
            )
        if self.include_completed:
            status_filters.append(
                {
                    "property": "状态",
                    "status": {"equals": "已完成"},
                }
            )

        if not status_filters:
            return []

        # 构建查询过滤器
        # 筛选条件：状态为进行中或已完成，且更新时间在本周内
        query_filter = {
            "and": [
                {"or": status_filters},
                {
                    "property": "更新时间：",
                    "last_edited_time": {
                        "on_or_after": monday.isoformat(),
                    },
                },
                {
                    "property": "更新时间：",
                    "last_edited_time": {
                        "on_or_before": sunday.isoformat(),
                    },
                },
            ]
        }

        # 查询数据库（使用 data_sources.query API）
        results = self.client.data_sources.query(
            data_source_id=self.task_tracker_db_id,
            filter=query_filter,
            sorts=[
                {
                    "property": "更新时间：",
                    "direction": "descending",
                }
            ],
        )

        tasks = []
        for page in results.get("results", []):
            task = self._extract_task_from_page(page)
            if task.name:  # 只添加有名称的任务
                tasks.append(task)

        # 构建层级关系
        return self._build_task_hierarchy(tasks)

    def get_weekly_tasks_flat(self) -> list[Task]:
        """获取本周的任务列表（扁平结构，包含父任务名称）"""
        monday, sunday = self.get_week_range()

        # 构建状态过滤条件
        status_filters = []
        if self.include_in_progress:
            status_filters.append(
                {
                    "property": "状态",
                    "status": {"equals": "进行中"},
                }
            )
        if self.include_completed:
            status_filters.append(
                {
                    "property": "状态",
                    "status": {"equals": "已完成"},
                }
            )

        if not status_filters:
            return []

        query_filter = {
            "and": [
                {"or": status_filters},
                {
                    "property": "更新时间：",
                    "last_edited_time": {
                        "on_or_after": monday.isoformat(),
                    },
                },
                {
                    "property": "更新时间：",
                    "last_edited_time": {
                        "on_or_before": sunday.isoformat(),
                    },
                },
            ]
        }

        results = self.client.data_sources.query(
            data_source_id=self.task_tracker_db_id,
            filter=query_filter,
            sorts=[
                {
                    "property": "更新时间：",
                    "direction": "descending",
                }
            ],
        )

        tasks = []
        task_map: dict[str, Task] = {}

        # 第一遍：提取所有任务
        for page in results.get("results", []):
            task = self._extract_task_from_page(page)
            if task.name:
                tasks.append(task)
                task_map[task.id] = task

        # 第二遍：填充父任务名称
        for task in tasks:
            if task.parent_task_ids:
                parent_id = task.parent_task_ids[0]
                if parent_id in task_map:
                    task.parent_task_name = task_map[parent_id].name
                else:
                    task.parent_task_name = self._get_page_title(parent_id)

        return tasks

    def create_weekly_report(
        self,
        title: str,
        content: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """创建周报页面"""
        # 创建页面
        new_page = self.client.pages.create(
            parent={"database_id": self.weekly_report_db_id},
            properties={
                "名称": {
                    "title": [
                        {
                            "text": {"content": title},
                        }
                    ]
                },
                "日期": {
                    "date": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                    }
                },
            },
            children=self._markdown_to_blocks(content),
        )

        return new_page

    def _markdown_to_blocks(self, markdown_content: str) -> list[dict[str, Any]]:
        """将 Markdown 内容转换为 Notion blocks"""
        blocks = []
        lines = markdown_content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # 跳过空行
            if not line.strip():
                i += 1
                continue

            # 处理标题
            if line.startswith("### "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[4:].strip()}}
                            ]
                        },
                    }
                )
            elif line.startswith("## "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[3:].strip()}}
                            ]
                        },
                    }
                )
            elif line.startswith("# "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line[2:].strip()}}
                            ]
                        },
                    }
                )
            # 处理无序列表
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                content = line.strip()[2:].strip()
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {"type": "text", "text": {"content": content}}
                            ]
                        },
                    }
                )
            # 处理有序列表
            elif line.strip() and line.strip()[0].isdigit() and ". " in line:
                content = (
                    line.strip().split(". ", 1)[1] if ". " in line else line.strip()
                )
                blocks.append(
                    {
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [
                                {"type": "text", "text": {"content": content}}
                            ]
                        },
                    }
                )
            # 处理分隔线
            elif line.strip() in ("---", "***", "___"):
                blocks.append(
                    {
                        "object": "block",
                        "type": "divider",
                        "divider": {},
                    }
                )
            # 普通段落
            else:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line.strip()}}
                            ]
                        },
                    }
                )

            i += 1

        return blocks
