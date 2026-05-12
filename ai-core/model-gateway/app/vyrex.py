"""Compatibility shim — re-exports the VyrexMiddleware implementation
that physically lives in ``app.vyrex``.

After the rename sweep, callers import from ``app.vyrex``. The underlying
module file was not renamed to avoid a large diff, so this module forwards
every public name to ``app.vyrex``.
"""
from __future__ import annotations

from app.vyrex import VyrexMiddleware  # noqa: F401

__all__ = ["VyrexMiddleware"]
