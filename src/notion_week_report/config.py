"""配置管理模块 - 支持 YAML 配置文件"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path("config.yaml")


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
