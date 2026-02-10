"""Mosaic puzzle solver.

Rules:
- Place black cells on the grid.
- Each number shows how many black cells are in the neighbouring cells
  (horizontally, vertically and diagonally) including the number cell itself.
"""

from .solver import BaseSolver


def _normalize_table(table):
    """Convert parser table to 0-based. Parser stores 0 as 2."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _neighborhood_cells(r, c, height, width):
    """Return list of (i, j) in the 3x3 neighborhood of (r, c) including (r, c)."""
    out = []
    for i in range(max(0, r - 1), min(height, r + 2)):
        for j in range(max(0, c - 1), min(width, c + 2)):
            out.append((i, j))
    return out


class MosaicSolver(BaseSolver):
    """Solver for Mosaic puzzles.

    Input: grid of clues (0-9) from TableTaskParser. 0 is stored as 2 by parser.
    Output: 2D grid with 0 = white, 1 = black.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.clues = _normalize_table(info["table"])
        # board[r][c] = -1 unassigned, 0 white, 1 black
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]

        # Precompute for each clue cell (i, j) the list of grid cells in its neighborhood
        self._neighbors_of = {}
        for i in range(self.height):
            for j in range(self.width):
                self._neighbors_of[(i, j)] = _neighborhood_cells(i, j, self.height, self.width)

        # For each (r, c), list of (i, j) clue cells whose neighborhood contains (r, c)
        self._clues_affected_by = {}
        for r in range(self.height):
            for c in range(self.width):
                self._clues_affected_by[(r, c)] = [
                    (i, j) for i in range(max(0, r - 1), min(self.height, r + 2))
                    for j in range(max(0, c - 1), min(self.width, c + 2))
                ]

    def _count_black_in_neighborhood(self, i, j):
        """Count assigned black cells (1) in the neighborhood of clue at (i, j)."""
        return sum(
            1 for (r, c) in self._neighbors_of[(i, j)]
            if self.board[r][c] == 1
        )

    def _unassigned_in_neighborhood(self, i, j):
        """Count unassigned cells (-1) in the neighborhood of clue at (i, j)."""
        return sum(
            1 for (r, c) in self._neighbors_of[(i, j)]
            if self.board[r][c] == -1
        )

    def _clue_ok_after_set(self, r, c, value):
        """After setting board[r][c] = value, check all affected clues are consistent."""
        for (i, j) in self._clues_affected_by[(r, c)]:
            target = self.clues[i][j]
            black = self._count_black_in_neighborhood(i, j)
            unassigned = self._unassigned_in_neighborhood(i, j)
            if black > target:
                return False
            if unassigned == 0 and black != target:
                return False
        return True

    def solve(self):
        """Solve the Mosaic puzzle. Returns 2D grid with 0=white, 1=black."""
        call_count = [0]
        backtrack_count = [0]

        def solve_at(cell_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] >= 0)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=self.height * self.width,
                )

            if cell_idx >= self.height * self.width:
                return True

            r = cell_idx // self.width
            c = cell_idx % self.width

            for value in (0, 1):
                self.board[r][c] = value
                if self._clue_ok_after_set(r, c, value):
                    if solve_at(cell_idx + 1):
                        return True
                self.board[r][c] = -1
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_at(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
