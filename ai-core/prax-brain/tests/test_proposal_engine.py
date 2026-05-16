from __future__ import annotations
import pytest
from prav.proposal_engine import ProposalEngine, Proposal
from prav.researcher import Idea

def test_create_proposal(mock_prax_dir):
    pe = ProposalEngine(mock_prax_dir)
    idea = Idea(title="Test Idea", source="test", url="https://example.com", description="A test idea")
    proposal = pe.create_proposal(idea)
    assert proposal.title == "Test Idea"
    assert proposal.proposal_id

def test_submit_and_check(mock_prax_dir):
    pe = ProposalEngine(mock_prax_dir)
    idea = Idea(title="Submit Test", source="test", url="https://example.com")
    proposal = pe.create_proposal(idea)
    pid = pe.submit_for_approval(proposal)
    assert pid == proposal.proposal_id
    assert pe.check_approval(pid) is None

def test_check_approved(mock_prax_dir):
    pe = ProposalEngine(mock_prax_dir)
    import json
    pid = "test-123"
    (mock_prax_dir / "proposals" / "approved" / f"{pid}.json").write_text(json.dumps({"proposal_id": pid}))
    assert pe.check_approval(pid) == "approved"
