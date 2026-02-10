"""Tents puzzle solver.

Rules:
- Pair each tree with a tent adjacent horizontally or vertically (1-to-1).
- Tents never touch each other, even diagonally.
- The clues outside the grid indicate the number of tents on that row/column.
"""

from .solver import BaseSolver


# 4 directions: right, down, left, up (adjacent for tree–tent pairing)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]
# 8 directions (including diagonals) for no-touch constraint
_D8 = [(0, 1), (1, 0), (0, -1), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _normalize_table(table, height, width):
    """Convert parser table to grid: 1 = tree, 0 = empty. Parser stores 0 as 2."""
    grid = [[0] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            if r < len(table) and c < len(table[r]):
                v = table[r][c]
                # 1 = tree; 0 or 2 (parser's empty) = empty
                grid[r][c] = 1 if v == 1 else 0
    return grid


class TentsSolver(BaseSolver):
    """Solver for Tents puzzles.

    Input: table (trees=1, empty=0/2), horizontal_borders (row tent counts),
           vertical_borders (column tent counts).
    Output: 2D grid with 0 = no tent, 1 = tent (only on empty cells).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.grid = _normalize_table(info["table"], self.height, self.width)
        # board[r][c]: 0 = no tent, 1 = tent (placed on empty cells only)
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        # Row/column tent counts from clues (lists of one number per row/col)
        row_borders = info.get("horizontal_borders", [])
        col_borders = info.get("vertical_borders", [])
        self.row_clues = [row_borders[i] if i < len(row_borders) else 0 for i in range(self.height)]
        self.col_clues = [col_borders[j] if j < len(col_borders) else 0 for j in range(self.width)]
        # List of tree positions
        self.trees = [
            (r, c) for r in range(self.height) for c in range(self.width)
            if self.grid[r][c] == 1
        ]
        # For each tree, candidate tent cells (4-adjacent empty cells)
        self.tree_candidates = []
        for r, c in self.trees:
            cands = []
            for dr, dc in _D4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == 0:
                    cands.append((nr, nc))
            self.tree_candidates.append(cands)

    def _tent_touches_another(self, r, c, exclude=None):
        """True if (r,c) has any 8-adjacent cell that is a tent (or in used set)."""
        exclude = exclude or set()
        for dr, dc in _D8:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if (nr, nc) in exclude:
                    continue
                if self.board[nr][nc] == 1:
                    return True
        return False

    def _can_place_tent(self, r, c, used_cells):
        """True if we can place a tent at (r,c): empty cell, not used, no adjacent tent."""
        if self.grid[r][c] != 0:
            return False
        if (r, c) in used_cells:
            return False
        return not self._tent_touches_another(r, c, exclude=used_cells)

    def solve(self):
        """Solve the Tents puzzle. Returns 2D grid with 0=no tent, 1=tent."""
        call_count = [0]
        backtrack_count = [0]
        n_trees = len(self.trees)

        def solve_tree(tree_idx, used_cells, row_remaining, col_remaining):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=tree_idx,
                    total_cells=n_trees,
                )

            if tree_idx >= n_trees:
                # All trees assigned; check row/col counts are exactly met
                return all(row_remaining[r] == 0 for r in range(self.height)) and all(
                    col_remaining[c] == 0 for c in range(self.width)
                )

            r, c = self.trees[tree_idx]
            cands = self.tree_candidates[tree_idx]

            for tr, tc in cands:
                if not self._can_place_tent(tr, tc, used_cells):
                    continue
                if row_remaining[tr] <= 0 or col_remaining[tc] <= 0:
                    continue

                self.board[tr][tc] = 1
                used_cells.add((tr, tc))
                row_remaining[tr] -= 1
                col_remaining[tc] -= 1

                if solve_tree(tree_idx + 1, used_cells, row_remaining, col_remaining):
                    return True

                self.board[tr][tc] = 0
                used_cells.discard((tr, tc))
                row_remaining[tr] += 1
                col_remaining[tc] += 1
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            row_remaining = list(self.row_clues)
            col_remaining = list(self.col_clues)
            ok = solve_tree(0, set(), row_remaining, col_remaining)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
