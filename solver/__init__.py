"""Puzzle solver modules.

This package contains specialized solvers for different puzzle types.
Each solver extends BaseSolver and implements puzzle-specific solving logic.
"""

from . import sudoku_solver
from . import kakurasu_solver
from . import nonograms_solver
from . import star_battle_solver
from . import renzoku_solver
from . import futoshiki_solver
from . import skyscrapers_solver
from . import killer_sudoku_solver

from .solver import BaseSolver

__all__ = [
    "BaseSolver",
    "sudoku_solver",
    "kakurasu_solver",
    "nonograms_solver",
    "star_battle_solver",
    "renzoku_solver",
    "futoshiki_solver",
    "skyscrapers_solver",
    "killer_sudoku_solver",
]
