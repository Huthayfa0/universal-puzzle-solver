"""Yin Yang puzzle solver.

Rules:
- All black cells must be connected orthogonally in a single group.
- All white cells must be connected orthogonally in a single group.
- No 2x2 area may be entirely black or entirely white.
- Every cell is either black or white.
"""

from collections import deque

from .solver import BaseSolver


# 4 directions: right, down, left, up
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]

WHITE = 0
BLACK = 1
EMPTY = -1


def _normalize_cell(value):
    """Map parser output to EMPTY, BLACK, or WHITE."""
    if value in (2, None, ""):
        return EMPTY
    if value in ("B", "b", 1):
        return BLACK
    if value in ("W", "w", 0):
        return WHITE
    return EMPTY


def _connected_count(board, height, width, color):
    """Return the size of the connected component of `color` containing (start_r, start_c).
    If no cell has that color, return 0. Uses BFS from first cell of that color.
    """
    start = None
    total = 0
    for r in range(height):
        for c in range(width):
            if board[r][c] == color:
                total += 1
                if start is None:
                    start = (r, c)
    if start is None or total == 0:
        return 0

    visited = [[False] * width for _ in range(height)]
    q = deque([start])
    visited[start[0]][start[1]] = True
    reached = 1
    while q:
        r, c = q.popleft()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and board[nr][nc] == color and not visited[nr][nc]:
                visited[nr][nc] = True
                reached += 1
                q.append((nr, nc))
    return reached


def _all_connected(board, height, width):
    """Return True iff all black cells form one component and all white cells form one component."""
    black_ok = _connected_count(board, height, width, BLACK) == sum(
        1 for r in range(height) for c in range(width) if board[r][c] == BLACK
    )
    white_ok = _connected_count(board, height, width, WHITE) == sum(
        1 for r in range(height) for c in range(width) if board[r][c] == WHITE
    )
    return black_ok and white_ok


def _has_2x2_same(board, height, width, r, c, color):
    """True if placing color at (r,c) would create a 2x2 block of that color."""
    def get(ri, ci):
        if (ri, ci) == (r, c):
            return color
        return board[ri][ci]

    for r0 in (r - 1, r):
        for c0 in (c - 1, c):
            if r0 < 0 or c0 < 0 or r0 + 1 >= height or c0 + 1 >= width:
                continue
            cells = [
                get(r0, c0), get(r0, c0 + 1),
                get(r0 + 1, c0), get(r0 + 1, c0 + 1),
            ]
            if all(x == color for x in cells):
                return True
    return False


class YinYangSolver(BaseSolver):
    """Solver for Yin Yang puzzles.

    Input: grid from TableTaskParser with binary=True; cells are 'W', 'B', or empty (2).
    Output: 2D grid with 0=white, 1=black (for TableSubmitter: 0=skip, 1=one click).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        raw = info.get("table", [])
        self.board = [[EMPTY for _ in range(self.width)] for _ in range(self.height)]
        for i in range(self.height):
            for j in range(self.width):
                if i < len(raw) and j < len(raw[i]):
                    self.board[i][j] = _normalize_cell(raw[i][j])

    def _cell_list(self):
        """Order empty cells for backtracking (e.g. row-major)."""
        return [(r, c) for r in range(self.height) for c in range(self.width) if self.board[r][c] == EMPTY]

    def solve(self):
        """Solve the Yin Yang puzzle. Returns 2D grid with 0=white, 1=black."""
        empty_cells = self._cell_list()
        call_count = [0]
        backtrack_count = [0]

        def solve_at(idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                filled = self.height * self.width - len(empty_cells) + idx
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=filled,
                    total_cells=self.height * self.width,
                )

            if idx >= len(empty_cells):
                return _all_connected(self.board, self.height, self.width)

            r, c = empty_cells[idx]
            for color in (BLACK, WHITE):
                if _has_2x2_same(self.board, self.height, self.width, r, c, color):
                    continue
                self.board[r][c] = color
                if solve_at(idx + 1):
                    return True
                self.board[r][c] = EMPTY
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
