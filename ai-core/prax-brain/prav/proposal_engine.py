from __future__ import annotations
import json, logging, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PRAX_DIR = Path(os.getenv("PRAX_DATA_DIR", "/var/prax"))

@dataclass
class Proposal:
    proposal_id: str
    title: str
    problem_statement: str
    solution_architecture: str
    tech_stack: list[str] = field(default_factory=list)
    estimated_effort: str = ""
    status: str = "pending"
    created_ts: str = ""

class ProposalEngine:
    def __init__(self, prax_dir: Path | None = None):
        self.prax_dir = prax_dir or PRAX_DIR
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        for d in ["proposals/pending", "proposals/approved", "proposals/rejected", "projects", "logs"]:
            (self.prax_dir / d).mkdir(parents=True, exist_ok=True)
    
    def create_proposal(self, idea: Any) -> Proposal:
        proposal = Proposal(
            proposal_id=str(uuid.uuid4())[:8],
            title=idea.title if hasattr(idea, 'title') else str(idea),
            problem_statement=idea.description if hasattr(idea, 'description') else "",
            solution_architecture=f"Full implementation of: {idea.title if hasattr(idea, 'title') else str(idea)}",
            tech_stack=["Python", "FastAPI", "Docker"],
            estimated_effort="4-8 hours",
            created_ts=datetime.now(timezone.utc).isoformat(),
        )
        return proposal
    
    def submit_for_approval(self, proposal: Proposal) -> str:
        pending_dir = self.prax_dir / "proposals" / "pending"
        path = pending_dir / f"{proposal.proposal_id}.json"
        with open(path, "w") as f:
            json.dump({
                "proposal_id": proposal.proposal_id,
                "title": proposal.title,
                "problem_statement": proposal.problem_statement,
                "solution_architecture": proposal.solution_architecture,
                "tech_stack": proposal.tech_stack,
                "estimated_effort": proposal.estimated_effort,
                "status": "pending",
                "created_ts": proposal.created_ts,
            }, f, indent=2)
        logger.info("Proposal %s submitted for approval", proposal.proposal_id)
        return proposal.proposal_id
    
    def check_approval(self, proposal_id: str) -> str | None:
        approved_dir = self.prax_dir / "proposals" / "approved"
        rejected_dir = self.prax_dir / "proposals" / "rejected"
        approved_path = approved_dir / f"{proposal_id}.json"
        rejected_path = rejected_dir / f"{proposal_id}.json"
        if approved_path.exists():
            return "approved"
        if rejected_path.exists():
            return "rejected"
        return None
