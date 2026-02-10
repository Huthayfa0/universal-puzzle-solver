"""Norinori puzzle solver.

Rules:
- Shade some cells so that exactly 2 cells are shaded in each region.
- Each shaded cell is part of a domino (two adjacent cells, 1x2 or 2x1). Dominoes may cross region borders.
- Dominoes cannot touch each other except diagonally (no edge-adjacency between different dominoes).
"""

from .solver import BaseSolver


# 4 directions (up, down, left, right — no diagonals)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


class NorinoriSolver(BaseSolver):
    """Solver for Norinori puzzles.

    Uses regions (boxes) from BoxesTaskParser. Board: 0 = unshaded, 1 = shaded.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.num_regions = len(self.boxes)

    def _remaining_per_region(self):
        """Return list of how many shaded cells each region still needs (2 - current count)."""
        rem = [2] * self.num_regions
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 1:
                    rem[self.boxes_table[i][j]] -= 1
        return rem

    def _has_adjacent_shaded(self, i, j, exclude=None):
        """True if any 4-neighbor of (i,j) is shaded, excluding cells in exclude (set of (r,c))."""
        exclude = exclude or set()
        for di, dj in _D4:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.height and 0 <= nj < self.width:
                if (ni, nj) not in exclude and self.board[ni][nj] == 1:
                    return True
        return False

    def _can_place_domino(self, i, j, ni, nj):
        """Check we can place a domino on (i,j) and (ni,nj): no other shaded 4-adjacent to either cell."""
        pair = {(i, j), (ni, nj)}
        if self._has_adjacent_shaded(i, j, exclude=pair):
            return False
        if self._has_adjacent_shaded(ni, nj, exclude=pair):
            return False
        return True

    def solve(self):
        """Solve the Norinori puzzle. Returns 2D board with 0=unshaded, 1=shaded."""
        rem = self._remaining_per_region()
        if any(r < 0 or r > 2 for r in rem):
            return None

        # Order regions (e.g. by size) for more deterministic backtracking
        self._region_order = list(range(self.num_regions))
        self._region_order.sort(key=lambda r: (len(self.boxes[r]), r))

        backtrack_count = [0]
        call_count = [0]

        def solve_with_progress(rem, region_order_idx):
            call_count[0] += 1
            shaded = sum(1 for i in range(self.height) for j in range(self.width) if self.board[i][j] == 1)
            if self.progress_tracker and call_count[0] % 500 == 0:
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=shaded,
                    total_cells=2 * self.num_regions,
                )

            if region_order_idx >= self.num_regions:
                return all(r == 0 for r in rem)

            rid = self._region_order[region_order_idx]
            if rem[rid] == 0:
                return solve_with_progress(rem, region_order_idx + 1)

            cells_in_region = self.boxes[rid]
            for i, j in cells_in_region:
                if self.board[i][j] == 1:
                    continue
                for di, dj in _D4:
                    ni, nj = i + di, j + dj
                    if not (0 <= ni < self.height and 0 <= nj < self.width):
                        continue
                    if self.board[ni][nj] == 1:
                        continue
                    r2 = self.boxes_table[ni][nj]
                    if rem[r2] == 0:
                        continue
                    if not self._can_place_domino(i, j, ni, nj):
                        continue

                    self.board[i][j] = 1
                    self.board[ni][nj] = 1
                    rem[rid] -= 1
                    rem[r2] -= 1

                    next_idx = region_order_idx + (1 if rem[rid] == 0 else 0)
                    if solve_with_progress(rem, next_idx):
                        return True

                    self.board[i][j] = 0
                    self.board[ni][nj] = 0
                    rem[rid] += 1
                    rem[r2] += 1
                    backtrack_count[0] += 1

            if rem[rid] == 0:
                return solve_with_progress(rem, region_order_idx + 1)
            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_with_progress(rem, 0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [row[:] for row in self.board]
