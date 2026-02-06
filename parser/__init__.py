"""Puzzle parsing modules.

This package contains parsers that convert raw puzzle data from the webpage
into structured formats suitable for solving.
"""

from .parser import (
    extract_task,
    validate_puzzle_page,
    PuzzlePageError,
    TaskParserBase,
    TableTaskParser,
    BorderTaskParser,
    BoxesTaskParser,
    CellTableTaskParser,
    CombinedTaskParser,
)

__all__ = [
    "extract_task",
    "validate_puzzle_page",
    "PuzzlePageError",
    "TaskParserBase",
    "TableTaskParser",
    "BorderTaskParser",
    "BoxesTaskParser",
    "CellTableTaskParser",
    "CombinedTaskParser",
]