"""Stitches puzzle solver.

Rules:
- Connect each block with ALL its neighbor blocks with exactly K "stitches" each
  (K=1 for 1÷, 2 for 2÷, 3 for 3÷, etc.).
- A stitch connects 2 orthogonally adjacent cells from different blocks.
- Two stitches cannot share a hole (each hole is used by at most one stitch).
- Row/column clues indicate the number of holes on that row/column.
"""

from .solver import BaseSolver
from itertools import combinations

_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _clue_val(x):
    """Extract numeric clue from border value (int or list)."""
    if isinstance(x, int):
        return x
    if isinstance(x, list) and x:
        return sum(x) if all(isinstance(v, int) for v in x) else (x[0] if isinstance(x[0], int) else 0)
    return 0


class StitchesSolver(BaseSolver):
    """Solver for Stitches puzzles.

    Uses CombinedTaskParser(BorderTaskParser, BoxesTaskParser):
    - Border part: row/column hole counts (horizontal_borders, vertical_borders).
    - Boxes part: regions (boxes), boxes_table, boxes_borders.

    Solution: 2D grid of hole counts per cell (number of stitches incident to that cell).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.height = info.get("height_2", info["height"])
        self.width = info.get("width_2", info["width"])
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        self.boxes_borders = info["boxes_borders"]
        self.num_boxes = len(self.boxes)

        row_borders = info.get("horizontal_borders") or []
        col_borders = info.get("vertical_borders") or []
        self.row_clues = [_clue_val(row_borders[i]) if i < len(row_borders) else 0 for i in range(self.height)]
        self.col_clues = [_clue_val(col_borders[j]) if j < len(col_borders) else 0 for j in range(self.width)]

        self.stitches_per_pair = info.get("stitches_per_pair", 1)

        self._build_block_pairs_and_edges()
        self.degree = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.stitches = set()

    def _build_block_pairs_and_edges(self):
        """Build list of (b1, b2) pairs and for each pair the list of edges ((r1,c1),(r2,c2))."""
        pair_set = set()
        for b1 in range(self.num_boxes):
            for b2 in self.boxes_borders[b1]:
                pair_set.add((min(b1, b2), max(b1, b2)))
        self.block_pairs = sorted(pair_set)

        self.pair_edges = []
        for (b1, b2) in self.block_pairs:
            edges = []
            for (i, j, direction) in self.boxes_borders[b1].get(b2, []):
                ni, nj = i + direction[0], j + direction[1]
                cell_a, cell_b = (i, j), (ni, nj)
                if cell_a > cell_b:
                    cell_a, cell_b = cell_b, cell_a
                edge = (cell_a, cell_b)
                if edge not in edges:
                    edges.append(edge)
            self.pair_edges.append(edges)

    def _row_sum(self, degree_grid, r):
        return sum(degree_grid[r][c] for c in range(self.width))

    def _col_sum(self, degree_grid, c):
        return sum(degree_grid[r][c] for r in range(self.height))

    def _apply_edges(self, degree_grid, edges, delta):
        for (a, b) in edges:
            r1, c1 = a
            r2, c2 = b
            degree_grid[r1][c1] += delta
            degree_grid[r2][c2] += delta

    def _can_add_edges(self, degree_grid, new_edges, pair_idx):
        """Check if adding new_edges keeps row/col sums within clues (no overshoot)."""
        for (a, b) in new_edges:
            r1, c1 = a
            r2, c2 = b
            degree_grid[r1][c1] += 1
            degree_grid[r2][c2] += 1
        for r in range(self.height):
            if self._row_sum(degree_grid, r) > self.row_clues[r]:
                self._apply_edges(degree_grid, new_edges, -1)
                return False
        for c in range(self.width):
            if self._col_sum(degree_grid, c) > self.col_clues[c]:
                self._apply_edges(degree_grid, new_edges, -1)
                return False
        self._apply_edges(degree_grid, new_edges, -1)
        return True

    def solve(self):
        """Solve the Stitches puzzle. Returns 2D grid of hole counts per cell."""
        total_holes = sum(self.row_clues)
        if total_holes != sum(self.col_clues):
            return None
        num_stitches = len(self.block_pairs) * self.stitches_per_pair
        if total_holes != 2 * num_stitches:
            return None

        degree_grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        chosen_stitches = set()
        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress(pair_idx, degree_grid, chosen_stitches):
            call_count[0] += 1
            if self.progress_tracker and call_count[0] % 500 == 0:
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    pairs_done=pair_idx,
                    total_pairs=len(self.block_pairs),
                )

            if pair_idx >= len(self.block_pairs):
                for r in range(self.height):
                    if self._row_sum(degree_grid, r) != self.row_clues[r]:
                        return False
                for c in range(self.width):
                    if self._col_sum(degree_grid, c) != self.col_clues[c]:
                        return False
                return True

            edges = self.pair_edges[pair_idx]
            K = self.stitches_per_pair
            if K > len(edges):
                return False

            for combo in combinations(edges, K):
                combo_list = list(combo)
                if not self._can_add_edges(degree_grid, combo_list, pair_idx):
                    continue
                self._apply_edges(degree_grid, combo_list, 1)
                for e in combo_list:
                    chosen_stitches.add((e[0], e[1]))

                if solve_with_progress(pair_idx + 1, degree_grid, chosen_stitches):
                    return True

                self._apply_edges(degree_grid, combo_list, -1)
                for e in combo_list:
                    chosen_stitches.discard((e[0], e[1]))
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_with_progress(0, degree_grid, chosen_stitches)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None

        self.stitches = chosen_stitches
        self.info["stitches"] = chosen_stitches
        return [degree_grid[r][:] for r in range(self.height)]
