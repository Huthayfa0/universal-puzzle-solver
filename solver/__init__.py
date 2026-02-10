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
from . import binairo_solver
from . import binairo_plus_solver
from . import norinori_solver
from . import dominosa_solver
from . import hitori_solver
from . import kurodoko_solver
from . import nurikabe_solver
from . import wordsearch_solver
from . import boggle_solver
from . import light_up_solver
from . import battleships_solver
from . import hashi_solver
from . import heyawake_solver
from . import masyu_solver
from . import shikaku_solver
from . import tents_solver
from . import lits_solver
from . import thermometers_solver
from . import galaxies_solver
from . import slither_link_solver
from . import minesweeper_solver
from . import shakashaka_solver
from . import pipes_solver
from . import tapa_solver
from . import yin_yang_solver
from . import slant_solver
from . import solo_chess_solver
from . import chess_ranger_solver
from . import chess_melee_solver

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
    "binairo_solver",
    "binairo_plus_solver",
    "norinori_solver",
    "dominosa_solver",
    "hitori_solver",
    "kurodoko_solver",
    "nurikabe_solver",
    "stitches_solver",
    "wordsearch_solver",
    "boggle_solver",
    "light_up_solver",
    "shingoki_solver",
    "battleships_solver",
    "hashi_solver",
    "heyawake_solver",
    "masyu_solver",
    "shikaku_solver",
    "tents_solver",
    "lits_solver",
    "mosaic_solver",
    "thermometers_solver",
    "galaxies_solver",
    "slither_link_solver",
    "minesweeper_solver",
    "shakashaka_solver",
    "kakuro_solver",
    "pipes_solver",
    "aquarium_solver",
    "tapa_solver",
    "yin_yang_solver",
    "slant_solver",
    "solo_chess_solver",
    "chess_ranger_solver",
    "chess_melee_solver",
]
