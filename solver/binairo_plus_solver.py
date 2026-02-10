"""Binairo+ solver. Same as Binairo (equal black/white, max two same adjacent) plus:
- Two cells with '=' between them must be the same color.
- Two cells with 'x' between them must be opposite colors.
- No row/column uniqueness (rectangular grid allowed).
"""

from .binairo_solver import BinairoSolver, EMPTY, BLACK, WHITE


class BinairoPlusSolver(BinairoSolver):
    """Binairo+ extends Binairo with same/opposite constraints between adjacent cells."""

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                        progress_interval=progress_interval, partial_interval=partial_interval)
        # Build constraint list: for each (r,c), list of ((nr, nc), 'same'|'opposite')
        self.constraint_neighbors = {}
        raw = info.get("cell_info_table", [])
        for i in range(self.height):
            for j in range(self.width):
                key = (i, j)
                self.constraint_neighbors[key] = []
                if i < len(raw) and j < len(raw[i]):
                    for (dr, dc), rel in raw[i][j]:
                        ni, nj = i + dr, j + dc
                        if 0 <= ni < self.height and 0 <= nj < self.width:
                            self.constraint_neighbors[key].append(((ni, nj), rel))

    def _constraints_ok_at(self, r, c):
        """Check that cell (r,c) satisfies all same/opposite constraints with its filled neighbors."""
        my_val = self.board[r][c]
        if my_val == EMPTY:
            return True
        for (nr, nc), rel in self.constraint_neighbors.get((r, c), []):
            other = self.board[nr][nc]
            if other == EMPTY:
                continue
            if rel == "same" and my_val != other:
                return False
            if rel == "opposite" and my_val == other:
                return False
        return True

    def _constraints_satisfied(self):
        """Check that every constraint edge is satisfied (both cells filled and same/opposite as required)."""
        for (r, c), neighbors in self.constraint_neighbors.items():
            if not self._constraints_ok_at(r, c):
                return False
        return True

    def _is_valid_placement(self, r, c, color):
        if not super()._is_valid_placement(r, c, color):
            return False
        self.board[r][c] = color
        ok = self._constraints_ok_at(r, c)
        self.board[r][c] = EMPTY
        return ok

    def _is_solution_complete(self):
        """Binairo+: no row/column uniqueness; require equal counts, no three adjacent, and all =/x constraints."""
        return (
            self._no_three_adjacent_anywhere()
            and self._all_counts_correct()
            and self._constraints_satisfied()
        )
