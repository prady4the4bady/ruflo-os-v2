from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
from typing import Optional

import requests


@dataclass
class DownloadSpec:
    source_type: str
    url: str
    file_name: str
    expected_sha256: str | None
    repo_hint: str | None = None


class DownloadError(RuntimeError):
    pass


class Downloader:
    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()

    def resolve_hf(self, repo: str, file_name: str) -> DownloadSpec:
        meta_url = f"https://huggingface.co/api/models/{repo}"
        response = self._session.get(meta_url, timeout=20)
        if response.status_code != 200:
            raise DownloadError(f"Hugging Face repo not found: {repo}")

        payload = response.json()
        siblings = payload.get("siblings") or []
        sibling = next((s for s in siblings if s.get("rfilename") == file_name), None)
        if sibling is None:
            raise DownloadError(f"File '{file_name}' not found in repo '{repo}'")

        expected_sha = None
        lfs = sibling.get("lfs") or {}
        if lfs.get("oid") and isinstance(lfs.get("oid"), str):
            expected_sha = str(lfs["oid"]).lower()

        url = f"https://huggingface.co/{repo}/resolve/main/{file_name}?download=true"
        return DownloadSpec(
            source_type="huggingface",
            url=url,
            file_name=file_name,
            expected_sha256=expected_sha,
            repo_hint=repo,
        )

    def resolve_github(self, url: str, expected_sha256: str | None = None) -> DownloadSpec:
        if "github.com/" not in url.lower():
            raise DownloadError("URL must be a GitHub release URL")

        head = self._session.head(url, allow_redirects=True, timeout=20)
        if head.status_code >= 400:
            raise DownloadError(f"GitHub URL is not reachable: {url}")

        final_name = url.rstrip("/").split("/")[-1]
        if not final_name:
            raise DownloadError("Could not derive filename from URL")

        return DownloadSpec(
            source_type="github",
            url=url,
            file_name=final_name,
            expected_sha256=expected_sha256.lower() if expected_sha256 else None,
            repo_hint=None,
        )

    def download_file(self, spec: DownloadSpec, target_dir: Path) -> tuple[Path, str]:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / spec.file_name

        with self._session.get(spec.url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with target_path.open("wb") as fh:
                shutil.copyfileobj(response.raw, fh)

        actual_sha = self.sha256(target_path)
        if spec.expected_sha256 and actual_sha != spec.expected_sha256.lower():
            target_path.unlink(missing_ok=True)
            raise DownloadError(
                f"SHA256 mismatch for {spec.file_name}: expected {spec.expected_sha256}, got {actual_sha}"
            )

        return target_path, actual_sha

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
