"""GitHub API 客户端模块 - 获取仓库提交历史"""

import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field


class GitCommit(BaseModel):
    """Git 提交数据模型"""

    sha: str = Field(description="提交 SHA")
    message: str = Field(description="提交信息")
    author: str = Field(description="提交作者")
    date: str = Field(description="提交日期")
    url: str = Field(description="提交链接")


class GitHubService:
    """GitHub 服务类"""

    # GitHub URL 正则表达式
    GITHUB_URL_PATTERN = re.compile(
        r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/?.*"
    )

    def __init__(self, token: str | None = None):
        """初始化 GitHub 服务

        Args:
            token: GitHub Personal Access Token（可选，用于提高 API 限制）
        """
        self.token = token
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> dict[str, str]:
        """获取请求头"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "notion-week-report",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def parse_github_url(self, url: str) -> tuple[str, str] | None:
        """解析 GitHub URL，提取 owner 和 repo

        Args:
            url: GitHub 仓库 URL

        Returns:
            (owner, repo) 元组，如果解析失败返回 None
        """
        if not url:
            return None

        match = self.GITHUB_URL_PATTERN.match(url)
        if match:
            owner = match.group("owner")
            repo = match.group("repo")
            # 移除 .git 后缀
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo

        return None

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
        per_page: int = 100,
    ) -> list[GitCommit]:
        """获取仓库提交历史

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            since: 起始时间（ISO 8601 格式）
            until: 结束时间（ISO 8601 格式）
            per_page: 每页返回数量

        Returns:
            GitCommit 列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"

        params: dict[str, Any] = {
            "per_page": per_page,
        }

        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                )

                if response.status_code == 404:
                    # 仓库不存在或无权限访问
                    return []

                if response.status_code == 403:
                    # API 限制
                    print(f"    ⚠️ GitHub API 限制，请配置 GitHub Token")
                    return []

                response.raise_for_status()
                data = response.json()

                commits = []
                for item in data:
                    commit_data = item.get("commit", {})
                    author_data = commit_data.get("author", {})

                    commits.append(
                        GitCommit(
                            sha=item.get("sha", "")[:7],  # 短 SHA
                            message=commit_data.get("message", "").split("\n")[
                                0
                            ],  # 只取第一行
                            author=author_data.get("name", "Unknown"),
                            date=author_data.get("date", ""),
                            url=item.get("html_url", ""),
                        )
                    )

                return commits

        except httpx.HTTPStatusError as e:
            print(f"    ⚠️ 获取 {owner}/{repo} 提交历史失败: HTTP {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            print(f"    ⚠️ 请求 GitHub API 失败: {e}")
            return []
        except Exception as e:
            print(f"    ⚠️ 处理提交历史时出错: {e}")
            return []

    def get_weekly_commits(
        self,
        repo_url: str,
        week_start: datetime,
        week_end: datetime,
    ) -> list[GitCommit]:
        """获取指定仓库本周的提交

        Args:
            repo_url: GitHub 仓库 URL
            week_start: 本周开始时间
            week_end: 本周结束时间

        Returns:
            GitCommit 列表
        """
        parsed = self.parse_github_url(repo_url)
        if not parsed:
            return []

        owner, repo = parsed
        return self.get_commits(
            owner=owner,
            repo=repo,
            since=week_start,
            until=week_end,
        )

