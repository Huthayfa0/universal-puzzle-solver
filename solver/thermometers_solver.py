"""Thermometers (Thermometers curved) puzzle solver.

Rules:
- Fill some thermometers with mercury starting from the bulb and going toward
  the end without gaps.
- The numbers outside the grid show the number of filled cells horizontally and
  vertically (per row and per column).
"""

from .solver import BaseSolver


def _clue_val(x):
    """Extract numeric clue from border value (int or list)."""
    if isinstance(x, int):
        return x
    if isinstance(x, list) and x:
        return sum(x) if all(isinstance(v, int) for v in x) else (x[0] if isinstance(x[0], int) else 0)
    return 0


class ThermometersSolver(BaseSolver):
    """Solver for Thermometers / Thermometers curved puzzles.

    Input: horizontal_borders (row filled counts), vertical_borders (column filled counts),
           thermometers = list of paths, each path = list of (r, c) from bulb to tip.
    Output: 2D grid with 0 = empty, 1 = filled (mercury).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        row_borders = info.get("horizontal_borders", [])
        col_borders = info.get("vertical_borders", [])
        self.row_clues = [_clue_val(row_borders[i]) if i < len(row_borders) else 0 for i in range(self.height)]
        self.col_clues = [_clue_val(col_borders[j]) if j < len(col_borders) else 0 for j in range(self.width)]
        self.thermometers = info.get("thermometers", [])
        # board[r][c]: 0 = empty, 1 = filled
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def solve(self):
        """Solve the Thermometers puzzle. Returns 2D grid with 0=empty, 1=filled."""
        call_count = [0]
        backtrack_count = [0]
        n_thermos = len(self.thermometers)
        total_filled = sum(self.row_clues)
        if total_filled != sum(self.col_clues):
            return None

        def solve_thermo(thermo_idx, row_remaining, col_remaining, filled_so_far):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=thermo_idx,
                    total_cells=n_thermos,
                )

            if thermo_idx >= n_thermos:
                return row_remaining == [0] * self.height and col_remaining == [0] * self.width

            path = self.thermometers[thermo_idx]
            # Try each possible fill length: 0 (all empty) up to len(path) (all filled)
            for length in range(len(path) + 1):
                # Check: filling path[0:length] must not exceed any row/col remaining
                ok = True
                for i in range(length):
                    r, c = path[i]
                    if row_remaining[r] <= 0 or col_remaining[c] <= 0:
                        ok = False
                        break
                if not ok:
                    continue

                # Apply path[0:length] as filled
                for i in range(length):
                    r, c = path[i]
                    self.board[r][c] = 1
                    row_remaining[r] -= 1
                    col_remaining[c] -= 1
                filled_so_far += length

                # Prune: if total filled so far + max possible from remaining thermos < total_filled, skip? No, we're filling exactly. Prune: if any row_remaining or col_remaining goes negative (already ensured). Prune: if we've over-filled total (filled_so_far > total_filled)?
                if filled_so_far > total_filled:
                    pass  # will revert and try next
                elif solve_thermo(thermo_idx + 1, row_remaining, col_remaining, filled_so_far):
                    return True

                # Revert
                for i in range(length):
                    r, c = path[i]
                    self.board[r][c] = 0
                    row_remaining[r] += 1
                    col_remaining[c] += 1
                filled_so_far -= length
                if length > 0:
                    backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            row_remaining = list(self.row_clues)
            col_remaining = list(self.col_clues)
            ok = solve_thermo(0, row_remaining, col_remaining, 0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
