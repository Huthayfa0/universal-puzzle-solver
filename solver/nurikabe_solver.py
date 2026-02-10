"""Nurikabe puzzle solver.

Rules:
- Black cells (nurikabe/stream): all orthogonally contiguous, no numbers, no 2x2+ solid rectangles.
- White cells (islands): each number n sits in an n-omino of white cells; each island has exactly
  one numbered cell; every white cell belongs to exactly one island.
- Output: 0 = white (land), 1 = black (shaded). Solvers typically shade black and dot non-numbered white.
"""

from collections import deque

from .solver import BaseSolver


# 4 directions: right, down, left, up
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_table(table):
    """Convert parser table: 0 is stored as 2; empty = 0, positive = clue size."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _has_2x2_black(board, r, c, height, width):
    """True if (r,c) is black and some 2x2 block containing (r,c) is all black."""
    if board[r][c] != 1:
        return False
    for dr in (0, 1):
        for dc in (0, 1):
            r0, c0 = r - dr, c - dc
            if r0 < 0 or c0 < 0 or r0 + 1 >= height or c0 + 1 >= width:
                continue
            if (board[r0][c0] == 1 and board[r0][c0 + 1] == 1 and
                    board[r0 + 1][c0] == 1 and board[r0 + 1][c0 + 1] == 1):
                return True
    return False


def _white_cc_from(board, r, c, height, width, table):
    """From (r,c) over white cells only, return (size, clue_at_cell or None, has_multiple_clues).
    Only considers cells already assigned white (0)."""
    visited = [[False] * width for _ in range(height)]
    q = deque([(r, c)])
    visited[r][c] = True
    size = 0
    clue = None
    clue_count = 0
    while q:
        i, j = q.popleft()
        if board[i][j] != 0:
            continue
        size += 1
        if table[i][j] > 0:
            clue = table[i][j]
            clue_count += 1
        for di, dj in _D4:
            ni, nj = i + di, j + dj
            if 0 <= ni < height and 0 <= nj < width and not visited[ni][nj] and board[ni][nj] == 0:
                visited[ni][nj] = True
                q.append((ni, nj))
    return size, clue, clue_count


def _all_white_ccs_valid(board, height, width, table):
    """Check every white CC contains exactly one clue and size == clue; total white = sum(clues)."""
    total_white = sum(1 for r in range(height) for c in range(width) if board[r][c] == 0)
    expected_white = sum(table[r][c] for r in range(height) for c in range(width) if table[r][c] > 0)
    if total_white != expected_white:
        return False
    visited = [[False] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            if board[r][c] != 0 or visited[r][c]:
                continue
            size, clue, clue_count = _white_cc_from(board, r, c, height, width, table)
            if clue_count != 1 or clue is None or size != clue:
                return False
            # Mark this CC as visited
            q = deque([(r, c)])
            visited[r][c] = True
            while q:
                i, j = q.popleft()
                for di, dj in _D4:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < height and 0 <= nj < width and board[ni][nj] == 0 and not visited[ni][nj]:
                        visited[ni][nj] = True
                        q.append((ni, nj))
    return True


def _black_connected(board, height, width):
    """True iff all black (1) cells form a single connected component."""
    start = None
    black_count = 0
    for r in range(height):
        for c in range(width):
            if board[r][c] == 1:
                black_count += 1
                if start is None:
                    start = (r, c)
    if black_count == 0:
        return True
    if start is None:
        return True
    visited = [[False] * width for _ in range(height)]
    q = deque([start])
    visited[start[0]][start[1]] = True
    reached = 1
    while q:
        r, c = q.popleft()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and board[nr][nc] == 1 and not visited[nr][nc]:
                visited[nr][nc] = True
                reached += 1
                q.append((nr, nc))
    return reached == black_count


def _any_2x2_black(board, height, width):
    """True if any 2x2 block is all black."""
    for r in range(height - 1):
        for c in range(width - 1):
            if (board[r][c] == 1 and board[r][c + 1] == 1 and
                    board[r + 1][c] == 1 and board[r + 1][c + 1] == 1):
                return True
    return False


class NurikabeSolver(BaseSolver):
    """Solver for Nurikabe puzzles.

    Input: grid from TableTaskParser; 0 = no clue, positive = island size (clue).
    Output: 2D grid with 0 = white (land), 1 = black (nurikabe). Submit: 1 = shade, 0 = skip.
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
        # board[r][c]: -1 unassigned, 0 white, 1 black. Clue cells are fixed white.
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        for r in range(self.height):
            for c in range(self.width):
                if self.table[r][c] > 0:
                    self.board[r][c] = 0  # clue cells are white

    def _has_2x2_black_at(self, r, c):
        """True if setting (r,c) to black would create or complete a 2x2 black block."""
        return _has_2x2_black(self.board, r, c, self.height, self.width)

    def _white_cc_ok_after_add(self, r, c):
        """After setting (r,c) to white, the white CC containing (r,c) must have exactly one clue and size <= clue."""
        # Temporarily treat (r,c) as white for CC computation
        old = self.board[r][c]
        self.board[r][c] = 0
        size, clue, clue_count = _white_cc_from(self.board, r, c, self.height, self.width, self.table)
        self.board[r][c] = old
        if clue_count == 0:
            return False  # white region with no clue is invalid
        if clue_count > 1:
            return False  # one island per clue
        return size <= clue

    def solve(self):
        """Solve the Nurikabe puzzle. Returns 2D grid with 0=white, 1=black."""
        call_count = [0]
        backtrack_count = [0]
        n_cells = self.height * self.width

        def solve_with_progress(cell_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] >= 0)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=n_cells,
                )

            if cell_idx >= n_cells:
                if not _all_white_ccs_valid(self.board, self.height, self.width, self.table):
                    return False
                if _any_2x2_black(self.board, self.height, self.width):
                    return False
                return _black_connected(self.board, self.height, self.width)

            r = cell_idx // self.width
            c = cell_idx % self.width

            if self.board[r][c] >= 0:
                return solve_with_progress(cell_idx + 1)  # already assigned (clue = white)

            # Option 1: black
            self.board[r][c] = 1
            if not self._has_2x2_black_at(r, c):
                if solve_with_progress(cell_idx + 1):
                    return True
            self.board[r][c] = -1
            backtrack_count[0] += 1

            # Option 2: white
            self.board[r][c] = 0
            if self._white_cc_ok_after_add(r, c):
                if solve_with_progress(cell_idx + 1):
                    return True
            self.board[r][c] = -1
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
