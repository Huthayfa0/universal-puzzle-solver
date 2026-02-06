"""Solution submission modules.

This package contains code for submitting solved puzzles back to
the webpage using browser automation.
"""

from .submitter import (
    SubmitterBase,
    TableSubmitter,
    WallsSubmitter,
    WallsAndTablesSubmitter,
    smart_click,
    smart_write,
    smart_write_number,
)

__all__ = [
    "SubmitterBase",
    "TableSubmitter",
    "WallsSubmitter",
    "WallsAndTablesSubmitter",
    "smart_click",
    "smart_write",
    "smart_write_number",
]