"""Minesweeper puzzle solver.

Rules:
- Find where the mines are.
- Numbers show how many mines are in the neighbouring cells (horizontally,
  vertically and diagonally).
- Right click to place a flag. Left click to open a cell.
"""

from .solver import BaseSolver


# Cell states during solving
UNKNOWN = -1
SAFE = 0
MINE = 1

# 8 neighbours: horizontal, vertical, diagonal
_D8 = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def _normalize_table(table, height, width):
    """Convert parser table to clue grid.
    Parser stores 0 as 2. Clue cells are 0-8; unrevealed/other -> UNKNOWN (-1).
    """
    grid = []
    for r in range(height):
        row = []
        for c in range(width):
            v = table[r][c]
            if isinstance(v, int):
                if v == 2:  # parser encodes 0 as 2
                    row.append(0)
                elif 0 <= v <= 8:
                    row.append(v)
                else:
                    row.append(UNKNOWN)
            else:
                row.append(UNKNOWN)
        grid.append(row)
    return grid


def _neighbors(r, c, height, width):
    """Yield (nr, nc) for all 8 neighbors of (r, c) in bounds."""
    for dr, dc in _D8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < height and 0 <= nc < width:
            yield (nr, nc)


class MinesweeperSolver(BaseSolver):
    """Solver for Minesweeper puzzles.

    Input: grid from TableTaskParser. 0-8 = clue (mines in 8 neighbors);
           9 or other = unrevealed (unknown).
    Output: 2D grid with 0 = safe, 1 = mine (flags).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.clue = _normalize_table(info["table"], self.height, self.width)
        # board[r][c]: SAFE=0, MINE=1, UNKNOWN=-1
        self.board = [[UNKNOWN for _ in range(self.width)] for _ in range(self.height)]
        # Clue cells are not mines; we don't need to assign them, but we use them for constraints
        for r in range(self.height):
            for c in range(self.width):
                if 0 <= self.clue[r][c] <= 8:
                    self.board[r][c] = SAFE  # clue cells are safe (no mine)

    def _clue_cells(self):
        """Yield (r, c, value) for each clue cell."""
        for r in range(self.height):
            for c in range(self.width):
                v = self.clue[r][c]
                if 0 <= v <= 8:
                    yield (r, c, v)

    def _count_neighbors(self, r, c, state):
        """Count neighbors of (r,c) that have given state (MINE or UNKNOWN)."""
        count = 0
        for nr, nc in _neighbors(r, c, self.height, self.width):
            if self.board[nr][nc] == state:
                count += 1
        return count

    def _unknown_neighbors(self, r, c):
        """List of (nr, nc) that are UNKNOWN neighbors of (r, c)."""
        return [(nr, nc) for nr, nc in _neighbors(r, c, self.height, self.width) if self.board[nr][nc] == UNKNOWN]

    def _propagate(self):
        """Apply logical deduction: if a clue forces mines or safe, set them.
        Returns True if any change, False if no change, None if invalid.
        """
        changed = False
        for r, c, need in self._clue_cells():
            mines = self._count_neighbors(r, c, MINE)
            unknowns = self._unknown_neighbors(r, c)
            k = len(unknowns)
            if k == 0:
                continue
            if mines > need:
                return None  # invalid
            if mines + k < need:
                return None  # invalid
            if mines + k == need:
                # all unknowns must be mines
                for nr, nc in unknowns:
                    self.board[nr][nc] = MINE
                    changed = True
            elif mines == need:
                # all unknowns must be safe
                for nr, nc in unknowns:
                    self.board[nr][nc] = SAFE
                    changed = True
        return changed

    def _all_satisfied(self):
        """Check that every clue has exactly the required number of mines in neighbors."""
        for r, c, need in self._clue_cells():
            if self._count_neighbors(r, c, MINE) != need:
                return False
        return True

    def _first_unknown(self):
        """Return (r, c) of first UNKNOWN cell, or None."""
        for r in range(self.height):
            for c in range(self.width):
                if self.board[r][c] == UNKNOWN:
                    return (r, c)
        return None

    def _solve(self):
        """Propagate then backtrack. Returns True if solution found."""
        while True:
            res = self._propagate()
            if res is None:
                return False
            if not res:
                break
        cell = self._first_unknown()
        if cell is None:
            return self._all_satisfied()
        r, c = cell
        for value in (MINE, SAFE):
            self.board[r][c] = value
            if self._solve():
                return True
            self.board[r][c] = UNKNOWN
        return False

    def solve(self):
        """Solve the Minesweeper puzzle. Returns 2D grid: 0 = safe, 1 = mine."""
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = self._solve()
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()
        if not ok:
            return None
        # Output: 0 = no mine, 1 = mine (for TableSubmitter / flags)
        return [[self.board[r][c] if self.board[r][c] != UNKNOWN else SAFE for c in range(self.width)] for r in range(self.height)]
