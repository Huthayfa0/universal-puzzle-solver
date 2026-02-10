"""Wordsearch puzzle solver.

Rules:
- Find all words from the list on the grid.
- Letters of each word lie in a straight line.
- Words can be horizontal, vertical, diagonal, or backwards.
- Puzzle is solved when all words are found.
"""

from .solver import BaseSolver

# 8 directions: E, W, S, N, SE, SW, NE, NW (row_delta, col_delta)
_DIRECTIONS = [
    (0, 1),   # right
    (0, -1),  # left
    (1, 0),   # down
    (-1, 0),  # up
    (1, 1),   # down-right
    (1, -1),  # down-left
    (-1, 1),  # up-right
    (-1, -1), # up-left
]


def _find_word_in_grid(grid, height, width, word, dr, dc):
    """Find first occurrence of word starting at any cell, in direction (dr, dc).
    Returns list of (r, c) path or None if not found.
    """
    word = word.upper()
    n = len(word)
    if n == 0:
        return []
    for r in range(height):
        for c in range(width):
            path = []
            nr, nc = r, c
            for i in range(n):
                if nr < 0 or nr >= height or nc < 0 or nc >= width:
                    break
                cell = grid[nr][nc]
                if isinstance(cell, str):
                    cell = cell.upper()
                else:
                    cell = str(cell).upper()
                if cell != word[i]:
                    break
                path.append((nr, nc))
                nr, nc = nr + dr, nc + dc
            if len(path) == n:
                return path
    return None


def _find_word(grid, height, width, word):
    """Find word in grid in any of the 8 directions. Returns path [(r,c), ...] or None."""
    for dr, dc in _DIRECTIONS:
        path = _find_word_in_grid(grid, height, width, word, dr, dc)
        if path is not None:
            return path
    return None


class WordsearchSolver(BaseSolver):
    """Solver for Wordsearch puzzles.

    Input: info with "table" (2D grid of letters) and "words" (list of words to find).
    Output: List of paths; each path is a list of (row, col) for one word, in order.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.grid = [row[:] for row in info["table"]]
        self.words = list(info.get("words", []))

    def solve(self):
        """Find all words on the grid. Returns list of paths (each path = list of (r, c))."""
        solution = []
        for idx, word in enumerate(self.words):
            if self.show_progress and self.progress_tracker:
                self._update_progress(
                    words_found=len(solution),
                    total_words=len(self.words),
                    current_word=word,
                )
            path = _find_word(self.grid, self.height, self.width, word)
            if path is None:
                return None
            solution.append(path)
        return solution
