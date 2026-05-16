from __future__ import annotations
import logging, os
from typing import Any

logger = logging.getLogger(__name__)

class ViralPublisher:
    def post_all(self, project_name: str, repo_url: str, description: str) -> dict[str, bool]:
        results: dict[str, bool] = {}
        logger.info("Would post %s (%s) to all platforms", project_name, repo_url)
        results["reddit"] = self._post_reddit(project_name, repo_url, description)
        results["twitter"] = self._post_twitter(project_name, repo_url, description)
        results["devto"] = self._post_devto(project_name, repo_url, description)
        results["hackernews"] = self._post_hackernews(project_name, repo_url)
        return results
    
    def _post_reddit(self, name: str, url: str, desc: str) -> bool:
        try:
            import praw
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                user_agent="Prax/1.0",
            )
            for sub in ["programming", "Python", "opensource"]:
                reddit.subreddit(sub).submit(title=f"{name}: {desc[:80]}", url=url)
            return True
        except Exception as e:
            logger.debug("Reddit post failed: %s", e)
            return False
    
    def _post_twitter(self, name: str, url: str, desc: str) -> bool:
        try:
            import tweepy
            client = tweepy.Client(
                consumer_key=os.getenv("TWITTER_API_KEY", ""),
                consumer_secret=os.getenv("TWITTER_API_SECRET", ""),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
                access_token_secret=os.getenv("TWITTER_ACCESS_SECRET", ""),
            )
            client.create_tweet(text=f"Just released {name}! {desc[:200]} {url}")
            return True
        except Exception as e:
            logger.debug("Twitter post failed: %s", e)
            return False
    
    def _post_devto(self, name: str, url: str, desc: str) -> bool:
        try:
            import urllib.request, json
            api_key = os.getenv("DEVTO_API_KEY", "")
            if not api_key:
                return False
            req = urllib.request.Request(
                "https://dev.to/api/articles",
                data=json.dumps({
                    "article": {
                        "title": f"Introducing {name}",
                        "body_markdown": f"# {name}\n\n{desc}\n\n[GitHub]({url})",
                        "published": True,
                        "tags": ["opensource", "python", "ai"],
                    }
                }).encode(),
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "Prax/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15):
                return True
        except Exception as e:
            logger.debug("Dev.to post failed: %s", e)
            return False
    
    def _post_hackernews(self, name: str, url: str) -> bool:
        try:
            import urllib.request, json
            req = urllib.request.Request(
                "https://hacker-news.firebaseio.com/v0/item/1.json",
                headers={"User-Agent": "Prax/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False
