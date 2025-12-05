"""配置管理模块 - 支持 YAML 配置文件"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path("config.yaml")

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个专业的周报撰写助手。你的任务是根据用户提供的任务列表，生成一份简洁、专业、有条理的周报。

要求：
1. 周报应该简洁明了，突出重点工作内容
2. 按照工作类型或项目进行分类整理
3. 对于已完成的任务，突出成果
4. 对于进行中的任务，说明当前进度
5. 使用专业但易懂的语言
6. 输出格式为 Markdown，包含适当的标题和列表
7. 总字数控制在 300-500 字之间
8. 注意任务之间的层级关系，子任务应该归类到对应的父任务下
9. 如果任务包含 Git 提交记录，根据提交内容理解实际完成的工作，并整合到周报中

输出格式示例：
## 本周工作总结

### 已完成工作
- 工作项1：简要描述成果
  - 子任务1：具体完成内容
  - 子任务2：具体完成内容
- 工作项2：简要描述成果

### 进行中工作
- 工作项1：当前进度说明
  - 子任务1：进度说明
- 工作项2：当前进度说明

### 下周计划
- 基于进行中的工作，简要说明下周重点

---
*周报生成时间：{生成时间}*
"""

# 默认用户提示词模板
DEFAULT_USER_PROMPT_TEMPLATE = """请根据以下本周（{week_start} 至 {week_end}）的任务列表生成周报：

{task_descriptions}

请生成一份专业的周报总结。"""


class NotionConfig(BaseModel):
    """Notion 配置"""

    token: str = Field(description="Notion Integration Token")
    task_tracker_database_id: str = Field(
        default="2b736dfe-5c6e-80e9-8b29-000b666d8ece",
        description="任务跟踪器数据库 ID",
    )
    weekly_report_database_id: str = Field(
        default="2c036dfe-5c6e-8048-9650-000bb520be4e",
        description="周报数据库 ID",
    )


class PromptConfig(BaseModel):
    """AI 提示词配置"""

    system_prompt: str = Field(
        default=DEFAULT_SYSTEM_PROMPT,
        description="系统提示词，定义 AI 的角色和输出格式",
    )
    user_prompt_template: str = Field(
        default=DEFAULT_USER_PROMPT_TEMPLATE,
        description="用户提示词模板，支持 {week_start}, {week_end}, {task_descriptions} 变量",
    )
    temperature: float = Field(
        default=0.7,
        description="生成温度，控制输出的随机性 (0-1)",
    )
    max_tokens: int = Field(
        default=1500,
        description="最大生成 token 数",
    )


class DeepSeekConfig(BaseModel):
    """DeepSeek 配置"""

    api_key: str = Field(description="DeepSeek API Key")
    base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API Base URL",
    )
    model: str = Field(
        default="deepseek-chat",
        description="DeepSeek 模型名称",
    )


class GitHubConfig(BaseModel):
    """GitHub 配置"""

    token: str | None = Field(
        default=None,
        description="GitHub Personal Access Token（可选，用于提高 API 限制）",
    )
    enabled: bool = Field(
        default=True,
        description="是否启用 Git 提交历史获取",
    )


class ScheduleConfig(BaseModel):
    """定时任务配置"""

    day: str = Field(
        default="friday",
        description="定时执行日期 (monday/tuesday/wednesday/thursday/friday/saturday/sunday)",
    )
    time: str = Field(
        default="16:30",
        description="定时执行时间 (HH:MM 格式)",
    )


class ReportConfig(BaseModel):
    """周报生成配置"""

    include_in_progress: bool = Field(
        default=True,
        description="是否包含进行中的任务",
    )
    include_completed: bool = Field(
        default=True,
        description="是否包含已完成的任务",
    )


class Settings(BaseModel):
    """应用配置"""

    notion: NotionConfig
    deepseek: DeepSeekConfig
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    prompt: PromptConfig = Field(default_factory=PromptConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)

    # 兼容旧的属性访问方式
    @property
    def notion_token(self) -> str:
        return self.notion.token

    @property
    def task_tracker_database_id(self) -> str:
        return self.notion.task_tracker_database_id

    @property
    def weekly_report_database_id(self) -> str:
        return self.notion.weekly_report_database_id

    @property
    def deepseek_api_key(self) -> str:
        return self.deepseek.api_key

    @property
    def deepseek_base_url(self) -> str:
        return self.deepseek.base_url

    @property
    def deepseek_model(self) -> str:
        return self.deepseek.model

    @property
    def schedule_day(self) -> str:
        return self.schedule.day

    @property
    def schedule_time(self) -> str:
        return self.schedule.time

    @property
    def include_in_progress(self) -> bool:
        return self.report.include_in_progress

    @property
    def include_completed(self) -> bool:
        return self.report.include_completed

    # Prompt 相关属性
    @property
    def system_prompt(self) -> str:
        return self.prompt.system_prompt

    @property
    def user_prompt_template(self) -> str:
        return self.prompt.user_prompt_template

    @property
    def prompt_temperature(self) -> float:
        return self.prompt.temperature

    @property
    def prompt_max_tokens(self) -> int:
        return self.prompt.max_tokens

    # GitHub 相关属性
    @property
    def github_token(self) -> str | None:
        return self.github.token

    @property
    def github_enabled(self) -> bool:
        return self.github.enabled


def load_yaml_config(config_path: Path | str) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_settings(config_path: Path | str | None = None) -> Settings:
    """获取配置实例

    Args:
        config_path: 配置文件路径，默认为 config.yaml

    Returns:
        Settings 实例
    """
    if config_path is None:
        # 尝试多个默认路径
        possible_paths = [
            Path("config.yaml"),
            Path("/app/config/config.yaml"),  # Docker 挂载路径
            Path.home() / ".config" / "notion-week-report" / "config.yaml",
        ]

        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        else:
            raise FileNotFoundError(
                f"未找到配置文件，请创建 config.yaml 或指定配置文件路径。\n"
                f"尝试的路径: {[str(p) for p in possible_paths]}"
            )

    config_data = load_yaml_config(config_path)
    return Settings(**config_data)


# 全局配置实例缓存
_settings: Settings | None = None


def get_cached_settings(config_path: Path | str | None = None) -> Settings:
    """获取缓存的配置实例"""
    global _settings
    if _settings is None:
        _settings = get_settings(config_path)
    return _settings


def reset_settings():
    """重置配置缓存"""
    global _settings
    _settings = None
