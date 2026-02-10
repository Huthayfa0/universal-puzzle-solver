"""Aquarium puzzle solver.

Rules:
- The puzzle is played on a rectangular grid divided into blocks (aquariums).
- Fill aquariums with water up to a certain level or leave them empty.
- The water level in each aquarium is the same across its full width.
- Numbers outside the grid show the number of filled cells per row and per column.
"""

from .solver import BaseSolver


class AquariumSolver(BaseSolver):
    """Solver for Aquarium puzzles.

    Uses CombinedTaskParser(BorderTaskParser, BoxesTaskParser):
    - horizontal_borders: filled cell count for each row
    - vertical_borders: filled cell count for each column
    - boxes, boxes_table: aquarium regions

    Board: 0 = empty, 1 = filled (water). Water fills from the bottom of each
    aquarium: for threshold T (0..height), cells in the aquarium with row >= T
    are filled. T=height means the aquarium is empty.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.row_sums = list(info["horizontal_borders"])
        self.col_sums = list(info["vertical_borders"])
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.num_regions = len(self.boxes)

        # Precompute per-region cells that get filled for each threshold k (0..height)
        # threshold k: fill cells (r, c) in region where r >= k
        self._region_fill_cells = []
        for box_id in range(self.num_regions):
            cells = self.boxes[box_id]
            by_threshold = []
            for k in range(self.height + 1):
                fill = [(r, c) for r, c in cells if r >= k]
                by_threshold.append(fill)
            self._region_fill_cells.append(by_threshold)

    def _apply_region(self, box_id, threshold, row_rem, col_rem, add):
        """Apply or undo a region assignment. add=True to fill, False to undo."""
        delta = 1 if add else -1
        for r, c in self._region_fill_cells[box_id][threshold]:
            self.board[r][c] = 1 if add else 0
            row_rem[r] -= delta
            col_rem[c] -= delta

    def _can_apply(self, box_id, threshold, row_rem, col_rem):
        """Check if applying this region with threshold would keep row/col counts non-negative."""
        fill = self._region_fill_cells[box_id][threshold]
        for r, c in fill:
            row_rem[r] -= 1
            col_rem[c] -= 1
        valid = all(r >= 0 for r in row_rem) and all(c >= 0 for c in col_rem)
        for r, c in fill:
            row_rem[r] += 1
            col_rem[c] += 1
        return valid

    def solve(self):
        """Solve the Aquarium puzzle. Returns 2D board with 0=empty, 1=filled."""
        row_rem = list(self.row_sums)
        col_rem = list(self.col_sums)
        backtrack_count = [0]
        call_count = [0]

        def solve_regions(region_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                filled = sum(1 for i in range(self.height) for j in range(self.width) if self.board[i][j] == 1)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=filled,
                    total_cells=self.height * self.width,
                )

            if region_idx >= self.num_regions:
                return all(r == 0 for r in row_rem) and all(c == 0 for c in col_rem)

            for k in range(self.height + 1):
                if not self._can_apply(region_idx, k, row_rem, col_rem):
                    continue
                self._apply_region(region_idx, k, row_rem, col_rem, add=True)
                if solve_regions(region_idx + 1):
                    return True
                self._apply_region(region_idx, k, row_rem, col_rem, add=False)
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_regions(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [row[:] for row in self.board]
