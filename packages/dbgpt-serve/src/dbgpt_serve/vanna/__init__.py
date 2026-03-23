"""Vanna Serve Module.

This module provides API endpoints for Vanna training data management.
"""

from dbgpt_serve.vanna.api import init_endpoints, router

__all__ = ["router", "init_endpoints"]
