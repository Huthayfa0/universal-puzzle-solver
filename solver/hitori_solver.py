"""Hitori puzzle solver.

Rules:
- No number should appear more than once in a row or a column (shade duplicates).
- Two black (shaded) cells cannot be adjacent horizontally or vertically.
- All non-shaded cells must be connected in a single group (4-adjacency).
"""

from collections import deque

from .solver import BaseSolver


# 4 directions: right, down, left, up
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_table(table):
    """Convert parser table to 0-based digits. Parser stores 0 as 2."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _white_cells_connected(board, height, width):
    """Return True iff all unshaded (0) cells form a single connected component."""
    visited = [[False] * width for _ in range(height)]
    start = None
    white_count = 0
    for r in range(height):
        for c in range(width):
            if board[r][c] == 0:
                white_count += 1
                if start is None:
                    start = (r, c)
    if white_count == 0:
        return False
    if start is None:
        return True

    # BFS from start
    q = deque([start])
    visited[start[0]][start[1]] = True
    reached = 1
    while q:
        r, c = q.popleft()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and board[nr][nc] == 0 and not visited[nr][nc]:
                visited[nr][nc] = True
                reached += 1
                q.append((nr, nc))
    return reached == white_count


class HitoriSolver(BaseSolver):
    """Solver for Hitori puzzles.

    Input: grid of numbers (from TableTaskParser). 0 is stored as 2 by parser.
    Output: 2D grid with 0 = unshaded, 1 = shaded.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.table = _normalize_table(info["table"])
        # board[r][c] = 0 unshaded, 1 shaded, -1 unassigned
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        # For constraint 1: which numbers are already kept (unshaded) in each row/col
        self.row_used = [set() for _ in range(self.height)]
        self.col_used = [set() for _ in range(self.width)]

    def _has_adjacent_shaded(self, r, c, exclude=None):
        """True if any 4-neighbor of (r,c) is shaded (1), optionally excluding a cell."""
        exclude = exclude or set()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if (nr, nc) not in exclude and self.board[nr][nc] == 1:
                    return True
        return False

    def solve(self):
        """Solve the Hitori puzzle. Returns 2D grid with 0=unshaded, 1=shaded."""
        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress(cell_idx):
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
                return _white_cells_connected(self.board, self.height, self.width)

            r = cell_idx // self.width
            c = cell_idx % self.width
            val = self.table[r][c]

            # Option 1: shade this cell
            if not self._has_adjacent_shaded(r, c):
                self.board[r][c] = 1
                if solve_with_progress(cell_idx + 1):
                    return True
                self.board[r][c] = -1
                backtrack_count[0] += 1

            # Option 2: leave unshaded
            if val not in self.row_used[r] and val not in self.col_used[c]:
                self.board[r][c] = 0
                self.row_used[r].add(val)
                self.col_used[c].add(val)
                if solve_with_progress(cell_idx + 1):
                    return True
                self.board[r][c] = -1
                self.row_used[r].discard(val)
                self.col_used[c].discard(val)
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
