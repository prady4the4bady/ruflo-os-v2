"""Unit tests for the DAG implementation (no async needed)."""
from __future__ import annotations

import pytest

from app.dag import DAG


def test_empty_dag_not_complete():
    dag = DAG()
    assert not dag.is_complete()


def test_single_node_ready():
    dag = DAG()
    dag.add_node("a")
    assert dag.ready_to_run() == ["a"]


def test_dependency_blocks_execution():
    dag = DAG()
    dag.add_node("a")
    dag.add_node("b", depends_on=["a"])
    ready = dag.ready_to_run()
    assert ready == ["a"]
    assert "b" not in ready


def test_complete_after_all_done():
    dag = DAG()
    dag.add_node("a")
    dag.mark_running("a")
    dag.mark_complete("a")
    assert dag.is_complete()


def test_cycle_detection():
    dag = DAG()
    dag.add_node("a", depends_on=["b"])
    dag.add_node("b", depends_on=["a"])
    assert dag.has_cycle()


def test_no_cycle_linear_chain():
    dag = DAG()
    dag.add_node("a")
    dag.add_node("b", depends_on=["a"])
    dag.add_node("c", depends_on=["b"])
    assert not dag.has_cycle()


def test_parallel_independent_nodes_all_ready():
    dag = DAG()
    dag.add_node("x")
    dag.add_node("y")
    dag.add_node("z")
    ready = dag.ready_to_run()
    assert set(ready) == {"x", "y", "z"}


def test_diamond_dependency():
    dag = DAG()
    dag.add_node("root")
    dag.add_node("left", depends_on=["root"])
    dag.add_node("right", depends_on=["root"])
    dag.add_node("merge", depends_on=["left", "right"])

    # Only root ready first
    assert dag.ready_to_run() == ["root"]

    dag.mark_running("root")
    dag.mark_complete("root")
    ready = set(dag.ready_to_run())
    assert ready == {"left", "right"}

    dag.mark_running("left")
    dag.mark_complete("left")
    dag.mark_running("right")
    dag.mark_complete("right")
    assert dag.ready_to_run() == ["merge"]

    dag.mark_running("merge")
    dag.mark_complete("merge")
    assert dag.is_complete()


def test_has_failures():
    dag = DAG()
    dag.add_node("a")
    dag.mark_running("a")
    dag.mark_failed("a")
    assert dag.has_failures()
    assert dag.is_complete()  # failed is terminal


def test_statuses_dict():
    dag = DAG()
    dag.add_node("a")
    dag.add_node("b")
    dag.mark_running("a")
    dag.mark_complete("a")
    statuses = dag.statuses()
    assert statuses["a"] == "completed"
    assert statuses["b"] == "pending"


def test_missing_dep_treated_as_completed():
    """A dependency ID that was never added should be treated as already done."""
    dag = DAG()
    dag.add_node("b", depends_on=["ghost"])
    assert dag.ready_to_run() == ["b"]


def test_node_count():
    dag = DAG()
    dag.add_node("a")
    dag.add_node("b")
    assert dag.node_count() == 2
