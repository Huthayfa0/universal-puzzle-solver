"""Light Up puzzle solver.

Rules:
- Place light bulbs on white cells so every white cell is illuminated.
- A cell is illuminated by a bulb if they're in the same row or column with no black cells between them.
- No light bulb may illuminate another (no two bulbs in the same row/column with no black between).
- Numbered black cells: the number is how many bulbs share an edge with that cell (0-4).
"""

from .solver import BaseSolver


# Cell type constants for grid
WHITE = -2
BLACK_NO_NUMBER = -1
# Black with clue n (0-4) stored as n

# 4 directions: right, down, left, up (for adjacent bulbs)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_grid(table, height, width):
    """Convert parser table to grid: WHITE=-2, BLACK_NO_NUMBER=-1, black with clue 0-4 = 0..4.
    Parser: 0 is stored as 2; 'W'/'B' passed through. We treat 'W' or 2 as white;
    'B' or 5 as black no number; 0-4 as black with that many adjacent bulbs.
    """
    grid = [[WHITE] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            v = table[r][c]
            if v == "W" or v == 2:
                grid[r][c] = WHITE
            elif v == "B" or v == 5 or (isinstance(v, int) and v > 4):
                grid[r][c] = BLACK_NO_NUMBER
            elif isinstance(v, int) and 0 <= v <= 4:
                grid[r][c] = v  # black with 0-4 adjacent bulbs (2 treated as white above)
            else:
                grid[r][c] = WHITE
    return grid


class LightUpSolver(BaseSolver):
    """Solver for Light Up puzzles.

    Input: grid from TableTaskParser. 2=white, 5=black no number, 0-4=black with that clue.
    Output: 2D grid with 0=no bulb, 1=bulb (only on white cells).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.grid = _normalize_grid(info["table"], self.height, self.width)
        # board[r][c]: 0 = no bulb, 1 = bulb (only on white cells)
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.white_cells = [
            (r, c) for r in range(self.height) for c in range(self.width)
            if self.grid[r][c] == WHITE
        ]

    def _is_black(self, r, c):
        return self.grid[r][c] >= BLACK_NO_NUMBER and self.grid[r][c] != WHITE

    def _is_lit(self, r, c):
        """True if white cell (r,c) is illuminated by some bulb (same row/col, no black between)."""
        if self.grid[r][c] != WHITE:
            return True
        if self.board[r][c] == 1:
            return True
        # Check row left
        for cc in range(c - 1, -1, -1):
            if self._is_black(r, cc):
                break
            if self.board[r][cc] == 1:
                return True
        # Check row right
        for cc in range(c + 1, self.width):
            if self._is_black(r, cc):
                break
            if self.board[r][cc] == 1:
                return True
        # Check col up
        for rr in range(r - 1, -1, -1):
            if self._is_black(rr, c):
                break
            if self.board[rr][c] == 1:
                return True
        # Check col down
        for rr in range(r + 1, self.height):
            if self._is_black(rr, c):
                break
            if self.board[rr][c] == 1:
                return True
        return False

    def _would_bulb_see_another(self, r, c):
        """True if placing a bulb at (r,c) would see another bulb (same row/col, no black between)."""
        # Row left
        for cc in range(c - 1, -1, -1):
            if self._is_black(r, cc):
                break
            if self.board[r][cc] == 1:
                return True
        # Row right
        for cc in range(c + 1, self.width):
            if self._is_black(r, cc):
                break
            if self.board[r][cc] == 1:
                return True
        # Col up
        for rr in range(r - 1, -1, -1):
            if self._is_black(rr, c):
                break
            if self.board[rr][c] == 1:
                return True
        # Col down
        for rr in range(r + 1, self.height):
            if self._is_black(rr, c):
                break
            if self.board[rr][c] == 1:
                return True
        return False

    def _count_adjacent_bulbs(self, r, c):
        count = 0
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.board[nr][nc] == 1:
                count += 1
        return count

    def _black_constraints_ok(self, r, c):
        """Check black cell (r,c) and its neighbors: no over-count, and if all adj white are assigned, count must match."""
        val = self.grid[r][c]
        if val == BLACK_NO_NUMBER:
            return True
        count = self._count_adjacent_bulbs(r, c)
        if count > val:
            return False
        # Count how many adjacent white cells are still unassigned (we're doing white cells in order, so "unassigned" = later)
        adj_white = 0
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                adj_white += 1
        if count + adj_white < val:
            return False
        return True

    def _all_black_constraints_ok_around(self, r, c):
        """After placing/removing at (r,c), check all black neighbors and their neighbors."""
        cells_to_check = set()
        cells_to_check.add((r, c))
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                cells_to_check.add((nr, nc))
        for (rr, cc) in cells_to_check:
            if self._is_black(rr, cc) and not self._black_constraints_ok(rr, cc):
                return False
        return True

    def _all_white_lit(self):
        for r, c in self.white_cells:
            if not self._is_lit(r, c):
                return False
        return True

    def solve(self):
        """Solve the Light Up puzzle. Returns 2D grid with 0=no bulb, 1=bulb."""
        n = len(self.white_cells)
        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress(idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                bulbs = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] == 1)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=idx,
                    total_cells=n,
                )

            if idx >= n:
                return self._all_white_lit()

            r, c = self.white_cells[idx]

            # Option 1: place bulb
            if not self._would_bulb_see_another(r, c):
                self.board[r][c] = 1
                if self._all_black_constraints_ok_around(r, c) and solve_with_progress(idx + 1):
                    return True
                self.board[r][c] = 0
                backtrack_count[0] += 1

            # Option 2: no bulb (must still be lit by someone else eventually)
            if solve_with_progress(idx + 1):
                return True
            backtrack_count[0] += 1
            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_with_progress(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
