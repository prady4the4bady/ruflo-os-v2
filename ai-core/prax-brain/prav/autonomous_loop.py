from __future__ import annotations
import logging, os, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prav.researcher import Researcher
from prav.proposal_engine import ProposalEngine
from prav.project_builder import ProjectBuilder
from prav.github_publisher import GitHubPublisher
from prav.viral_publisher import ViralPublisher
from prav.mind_rewriter import MindRewriter

logger = logging.getLogger(__name__)

SCAN_INTERVAL = 6 * 3600
APPROVAL_POLL_INTERVAL = 1800
EVOLVE_INTERVAL = 7 * 86400
SELF_MODIFY_INTERVAL = 86400


@dataclass
class LoopState:
    running: bool = False
    last_scan_ts: str = ""
    last_evolve_ts: str = ""
    last_self_modify_ts: str = ""
    cycle_count: int = 0
    proposals_submitted: int = 0
    builds_completed: int = 0
    builds_succeeded: int = 0


class AutonomousLoop:
    def __init__(self, prax_dir: Path | None = None, poll_interval: int | None = None):
        self.prax_dir = prax_dir or Path(os.getenv("PRAX_DATA_DIR", "/var/prax"))
        # poll_interval=None -> default; poll_interval=0 -> non-blocking (test mode).
        self._poll_interval = APPROVAL_POLL_INTERVAL if poll_interval is None else poll_interval
        self.researcher = Researcher()
        self.proposal_engine = ProposalEngine(self.prax_dir)
        self.project_builder = ProjectBuilder(self.prax_dir)
        self.github_publisher = GitHubPublisher()
        self.viral_publisher = ViralPublisher()
        self.mind_rewriter = MindRewriter(self.prax_dir)
        self.state = LoopState()
        self._log_path = self.prax_dir / "logs" / "autonomous_loop.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        self.state.running = True
        logger.info("Autonomous loop started")
        while self.state.running:
            self._tick()

    def _tick(self) -> None:
        try:
            now = time.time()
            if now - self._ts_to_epoch(self.state.last_scan_ts) > SCAN_INTERVAL:
                self._research_and_propose()
                self.state.last_scan_ts = datetime.now(timezone.utc).isoformat()
            self._check_pending_approvals()
            if now - self._ts_to_epoch(self.state.last_evolve_ts) > EVOLVE_INTERVAL:
                self.mind_rewriter.evolve()
                self.state.last_evolve_ts = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            logger.error("Loop error: %s", e)
        finally:
            # Sleep only when requested and the loop is still running.
            # poll_interval=0 keeps the loop responsive (used by tests).
            if self._poll_interval > 0 and self.state.running:
                time.sleep(self._poll_interval)
    
    def stop(self) -> None:
        self.state.running = False
        logger.info("Autonomous loop stopped")
    
    def status(self) -> dict[str, Any]:
        return {
            "running": self.state.running,
            "cycle_count": self.state.cycle_count,
            "last_scan_ts": self.state.last_scan_ts,
            "last_evolve_ts": self.state.last_evolve_ts,
            "proposals_submitted": self.state.proposals_submitted,
            "builds_completed": self.state.builds_completed,
            "builds_succeeded": self.state.builds_succeeded,
        }
    
    def _research_and_propose(self) -> None:
        ideas = self.researcher.get_top_proposals(n=3)
        for idea in ideas:
            proposal = self.proposal_engine.create_proposal(idea)
            self.proposal_engine.submit_for_approval(proposal)
            self.state.proposals_submitted += 1
        self.state.cycle_count += 1
    
    def _check_pending_approvals(self) -> None:
        pending_dir = self.prax_dir / "proposals" / "pending"
        if not pending_dir.exists():
            return
        for f in pending_dir.glob("*.json"):
            import json
            proposal_id = f.stem
            status = self.proposal_engine.check_approval(proposal_id)
            if status == "approved":
                self._handle_approval(proposal_id)
                f.unlink(missing_ok=True)
            elif status == "rejected":
                f.unlink(missing_ok=True)
    
    def _handle_approval(self, proposal_id: str) -> None:
        approved_dir = self.prax_dir / "proposals" / "approved"
        path = approved_dir / f"{proposal_id}.json"
        if not path.exists():
            return
        import json
        with open(path) as f:
            data = json.load(f)
        from types import SimpleNamespace
        proposal = SimpleNamespace(**data)
        project_path = self.project_builder.scaffold(proposal)
        success = self.project_builder.iterate_until_green(project_path)
        self.state.builds_completed += 1
        if success:
            self.state.builds_succeeded += 1
            repo_url = self.github_publisher.create_repo(project_path.name, proposal.title)
            if repo_url:
                self.github_publisher.push_project(project_path, repo_url)
                self.github_publisher.create_release(project_path.name, "0.1.0")
                self.viral_publisher.post_all(project_path.name, repo_url, proposal.title)
    
    @staticmethod
    def _ts_to_epoch(ts: str) -> float:
        if not ts:
            return 0.0
        try:
            return datetime.fromisoformat(ts).timestamp()
        except (ValueError, TypeError):
            return 0.0


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    loop = AutonomousLoop()
    loop.run()


if __name__ == "__main__":
    main()
