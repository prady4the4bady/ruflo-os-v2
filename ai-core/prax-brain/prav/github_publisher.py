from __future__ import annotations
import logging, os, subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
ORG_NAME = "prady4the4bady"

class GitHubPublisher:
    def __init__(self, token: str = ""):
        self.token = token or GITHUB_TOKEN
    
    def create_repo(self, name: str, description: str = "") -> str | None:
        if not self.token:
            logger.warning("GITHUB_TOKEN not set, skipping repo creation")
            return None
        try:
            import urllib.request, json
            req = urllib.request.Request(
                "https://api.github.com/user/repos",
                data=json.dumps({"name": name, "description": description, "private": False}).encode(),
                headers={
                    "Authorization": f"token {self.token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Prax/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("html_url", f"https://github.com/{ORG_NAME}/{name}")
        except Exception as e:
            logger.error("Failed to create repo: %s", e)
            return None
    
    def push_project(self, project_path: Path, repo_url: str | None = None) -> bool:
        if not repo_url:
            repo_url = f"https://github.com/{ORG_NAME}/{project_path.name}.git"
        try:
            subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit [skip ci]"], cwd=project_path, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", repo_url],
                cwd=project_path, capture_output=True,
            )
            result = subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=project_path, capture_output=True, text=True,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error("Push failed: %s", e)
            return False
    
    def create_release(self, repo_name: str, version: str, changelog: str = "") -> bool:
        if not self.token:
            return False
        try:
            import urllib.request, json
            req = urllib.request.Request(
                f"https://api.github.com/repos/{ORG_NAME}/{repo_name}/releases",
                data=json.dumps({
                    "tag_name": f"v{version}",
                    "name": f"v{version}",
                    "body": changelog or f"Release v{version}",
                }).encode(),
                headers={
                    "Authorization": f"token {self.token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Prax/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status == 201
        except Exception as e:
            logger.error("Release failed: %s", e)
            return False
