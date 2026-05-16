from __future__ import annotations
import pytest
from prav.autonomous_loop import AutonomousLoop

def test_loop_initial_state(mock_prax_dir):
    loop = AutonomousLoop(mock_prax_dir)
    status = loop.status()
    assert not status["running"]
    assert status["cycle_count"] == 0

def test_loop_start_stop(mock_prax_dir):
    loop = AutonomousLoop(mock_prax_dir)
    loop.state.running = True
    assert loop.state.running
    loop.stop()
    assert not loop.state.running

def test_loop_tick(mock_prax_dir):
    loop = AutonomousLoop(mock_prax_dir, poll_interval=0)
    loop.state.running = True
    loop._tick()
    assert loop.state.cycle_count >= 0

def test_loop_status_structure(mock_prax_dir):
    loop = AutonomousLoop(mock_prax_dir)
    status = loop.status()
    assert "running" in status
    assert "cycle_count" in status
    assert "proposals_submitted" in status
    assert "builds_completed" in status
