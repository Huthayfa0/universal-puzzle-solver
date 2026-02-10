"""Shikaku puzzle solver.

Rules:
- Divide the grid into rectangular and square pieces.
- Each piece contains exactly one number.
- That number represents the area of the rectangle.
"""

from .solver import BaseSolver


def _factor_pairs(area):
    """Return list of (width, height) pairs such that width * height == area, width <= height for uniqueness of shape."""
    pairs = []
    for w in range(1, area + 1):
        if area % w == 0:
            h = area // w
            pairs.append((w, h))
    return pairs


def _rectangles_containing_cell(r0, c0, w, h, grid_height, grid_width):
    """Yield (r1, c1, r2, c2) top-left and bottom-right (inclusive) of rectangles of size w*h that contain (r0, c0)."""
    # Rectangle [r1, r1+h-1] x [c1, c1+w-1] must contain (r0, c0)
    # r1 <= r0 <= r1 + h - 1  =>  r1 in [max(0, r0 - h + 1), min(grid_height - h, r0)]
    # c1 <= c0 <= c1 + w - 1  =>  c1 in [max(0, c0 - w + 1), min(grid_width - w, c0)]
    r1_min = max(0, r0 - h + 1)
    r1_max = min(grid_height - h, r0)
    c1_min = max(0, c0 - w + 1)
    c1_max = min(grid_width - w, c0)
    for r1 in range(r1_min, r1_max + 1):
        for c1 in range(c1_min, c1_max + 1):
            yield (r1, c1, r1 + h - 1, c1 + w - 1)


def _normalize_table(table):
    """Convert parser table: 0 is stored as 2; treat as empty. Other values are clue areas."""
    return [[0 if c == 2 else c for c in row] for row in table]


class ShikakuSolver(BaseSolver):
    """Solver for Shikaku puzzles.

    Input: grid from TableTaskParser. Empty cells stored as 2 (treated as 0); clue cells have their area (1, 2, 3, ...).
    Output: 2D grid where each cell has a 1-based region ID (same ID for all cells in the same rectangle).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        table = _normalize_table(info["table"])
        # Clues: (r, c, area) for each cell that has a number
        self.clues = []
        for r in range(self.height):
            for c in range(self.width):
                val = table[r][c]
                if val > 0:
                    self.clues.append((r, c, val))
        # assignment[r][c] = clue_index (0-based) or -1
        self.assignment = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]  # 1-based for progress display

    def _can_place(self, r1, c1, r2, c2, clue_idx):
        """Check if rectangle [r1..r2] x [c1..c2] can be placed (all cells unassigned or same clue)."""
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.assignment[r][c] != -1 and self.assignment[r][c] != clue_idx:
                    return False
        return True

    def _place(self, r1, c1, r2, c2, clue_idx):
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                self.assignment[r][c] = clue_idx
                self.board[r][c] = clue_idx + 1

    def _unplace(self, r1, c1, r2, c2):
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                self.assignment[r][c] = -1
                self.board[r][c] = 0

    def _solve(self, clue_idx):
        if clue_idx >= len(self.clues):
            return True

        r0, c0, area = self.clues[clue_idx]

        if self.show_progress and self.progress_tracker:
            self._update_progress(
                clue_idx=clue_idx,
                total_clues=len(self.clues),
                clue_type="region",
            )

        # If this clue is already covered (by a rectangle we placed earlier that included it), skip
        if self.assignment[r0][c0] != -1 and self.assignment[r0][c0] != clue_idx:
            return False
        if self.assignment[r0][c0] == clue_idx:
            # Already placed for this clue (shouldn't happen at placement time)
            return self._solve(clue_idx + 1)

        for w, h in _factor_pairs(area):
            for r1, c1, r2, c2 in _rectangles_containing_cell(r0, c0, w, h, self.height, self.width):
                if not self._can_place(r1, c1, r2, c2, clue_idx):
                    continue
                self._place(r1, c1, r2, c2, clue_idx)
                if self._solve(clue_idx + 1):
                    return True
                self._unplace(r1, c1, r2, c2)

        return False

    def solve(self):
        """Solve the Shikaku puzzle. Returns 2D grid of 1-based region IDs."""
        total_cells = self.height * self.width
        total_area = sum(a for _, _, a in self.clues)
        if total_area != total_cells:
            return None

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()

        try:
            ok = self._solve(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None

        return [[self.assignment[r][c] + 1 for c in range(self.width)] for r in range(self.height)]
