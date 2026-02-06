"""Browser controller modules.

This package contains browser automation code for interacting with
the puzzles-mobile.com website.
"""

from .chrome_controller import get_driver

__all__ = ["get_driver"]