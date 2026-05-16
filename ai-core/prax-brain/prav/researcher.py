"""Idea researcher — monitors HN, arXiv, GitHub for novel buildable ideas."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SCORE_WEIGHTS = {"novelty": 0.3, "impact": 0.35, "buildability": 0.35}

IMPORTANT_DOMAINS = {
    "health", "education", "productivity", "climate",
    "finance", "security", "privacy", "accessibility",
}

# When PRAX_OFFLINE=1, source scanners short-circuit to an empty list.
# Tests and CI runs without internet should set this to keep the suite fast
# and deterministic.
_OFFLINE = os.getenv("PRAX_OFFLINE") in ("1", "true", "True", "yes")
_HTTP_TIMEOUT = float(os.getenv("PRAX_HTTP_TIMEOUT", "5"))


@dataclass
class Idea:
    title: str
    source: str
    url: str
    description: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class Researcher:
    def scan_sources(self) -> list[Idea]:
        ideas: list[Idea] = []
        ideas.extend(self._scan_hackernews())
        ideas.extend(self._scan_github_trending())
        return ideas

    def score_idea(self, idea: Idea) -> Idea:
        novelty = self._score_novelty(idea)
        impact = self._score_impact(idea)
        buildability = self._score_buildability(idea)
        idea.score = (
            novelty * SCORE_WEIGHTS["novelty"]
            + impact * SCORE_WEIGHTS["impact"]
            + buildability * SCORE_WEIGHTS["buildability"]
        )
        return idea

    def get_top_proposals(self, n: int = 5) -> list[Idea]:
        ideas = self.scan_sources()
        scored = [self.score_idea(i) for i in ideas]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:n]

    def _scan_hackernews(self) -> list[Idea]:
        if _OFFLINE:
            return []
        ideas: list[Idea] = []
        try:
            req = urllib.request.Request(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                headers={"User-Agent": "Prax/1.0"},
            )
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310 — fixed scheme
                ids = json.loads(resp.read())[:30]
            for sid in ids:
                try:
                    item_req = urllib.request.Request(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        headers={"User-Agent": "Prax/1.0"},
                    )
                    with urllib.request.urlopen(item_req, timeout=_HTTP_TIMEOUT) as ir:  # noqa: S310
                        item = json.loads(ir.read())
                    if item and item.get("title") and item.get("url"):
                        ideas.append(Idea(
                            title=item["title"], source="hackernews",
                            url=item["url"], description=item.get("text", ""),
                        ))
                except Exception:
                    continue
        except Exception as e:
            logger.debug("HN scan failed: %s", e)
        return ideas

    def _scan_github_trending(self) -> list[Idea]:
        if _OFFLINE:
            return []
        ideas: list[Idea] = []
        try:
            req = urllib.request.Request(
                "https://api.github.com/search/repositories?q=created:>2025-01-01&sort=stars&order=desc&per_page=10",
                headers={"User-Agent": "Prax/1.0", "Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # noqa: S310
                data = json.loads(resp.read())
            for repo in data.get("items", []):
                ideas.append(Idea(
                    title=repo.get("description") or repo["name"],
                    source="github-trending",
                    url=repo["html_url"],
                    description=repo.get("description") or "",
                    metadata={"stars": repo.get("stargazers_count", 0), "language": repo.get("language", "")},
                ))
        except Exception as e:
            logger.debug("GitHub scan failed: %s", e)
        return ideas

    def _score_novelty(self, idea: Idea) -> float:
        title_lower = idea.title.lower()
        if any(word in title_lower for word in ["new", "novel", "first", "breakthrough"]):
            return 0.9
        return 0.5

    def _score_impact(self, idea: Idea) -> float:
        desc_lower = (idea.title + " " + idea.description).lower()
        for domain in IMPORTANT_DOMAINS:
            if domain in desc_lower:
                return 0.9
        return 0.4

    def _score_buildability(self, idea: Idea) -> float:
        desc = idea.title + " " + idea.description
        word_count = len(desc.split())
        if 10 < word_count < 200:
            return 0.8
        return 0.5
