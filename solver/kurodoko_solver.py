"""Kurodoko puzzle solver.

Rules:
- Shade some cells black. Each number clue = total visible white cells (including itself)
  in straight lines up/down/left/right, stopped by black cells or grid edges.
- Numbered cells remain white (unshaded).
- All unshaded cells form a single orthogonally connected polyomino.
- Black cells cannot touch horizontally or vertically (diagonals allowed).
"""

from collections import deque

from .solver import BaseSolver


# 4 directions: right, down, left, up
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_table(table):
    """Convert parser table to 0-based. Parser stores 0 as 2; 0 = no clue."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _visible_white_count(board, height, width, r, c):
    """Count visible white cells from (r,c) in all 4 directions including self.
    Stops at black (1) or grid edge. (r,c) must be white (0).
    """
    if board[r][c] != 0:
        return 0
    total = 1
    for dr, dc in _D4:
        nr, nc = r + dr, c + dc
        while 0 <= nr < height and 0 <= nc < width and board[nr][nc] == 0:
            total += 1
            nr += dr
            nc += dc
    return total


def _white_cells_connected(board, height, width):
    """Return True iff all white (0) cells form a single connected component."""
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
        return True
    if start is None:
        return True

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


def _has_adjacent_black_hv(board, height, width, r, c, exclude=None):
    """True if any 4-neighbor of (r,c) is black (1), optionally excluding a cell."""
    exclude = exclude or set()
    for dr, dc in _D4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < height and 0 <= nc < width:
            if (nr, nc) not in exclude and board[nr][nc] == 1:
                return True
    return False


def _clue_satisfied(board, height, width, table, r, c):
    """True if clue at (r,c) has correct visible count (all cells in its rays assigned)."""
    clue = table[r][c]
    if clue <= 0:
        return True
    # Check that visibility is fully determined and correct
    count = _visible_white_count(board, height, width, r, c)
    return count == clue


def _visible_white_count_if_all_unknown_white(board, height, width, r, c):
    """Count visible from (r,c) treating -1 as white (upper bound for visibility)."""
    if board[r][c] == 1:
        return 0
    total = 1
    for dr, dc in _D4:
        nr, nc = r + dr, c + dc
        while 0 <= nr < height and 0 <= nc < width and board[nr][nc] != 1:
            total += 1
            nr += dr
            nc += dc
    return total


def _clue_visible_and_determined(board, height, width, r, c):
    """Return (visible_white_count, fully_determined). Fully determined when every ray hit black or edge."""
    if board[r][c] != 0:
        return (0, False)
    total = 1
    determined = True
    for dr, dc in _D4:
        nr, nc = r + dr, c + dc
        while 0 <= nr < height and 0 <= nc < width:
            if board[nr][nc] == 1:
                break
            if board[nr][nc] == -1:
                determined = False
                break
            total += 1
            nr += dr
            nc += dc
    return (total, determined)


def _all_clues_satisfied(board, height, width, table):
    """Check every clue cell has correct visible white count."""
    for r in range(height):
        for c in range(width):
            if table[r][c] > 0 and not _clue_satisfied(board, height, width, table, r, c):
                return False
    return True


class KurodokoSolver(BaseSolver):
    """Solver for Kurodoko puzzles.

    Input: grid from TableTaskParser. 0 = no clue (parser stores as 2), positive = clue value.
    Output: 2D grid with 0 = white (unshaded), 1 = black (shaded).
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
        # board[r][c]: -1 unassigned, 0 white, 1 black
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]

    def _solve(self, cell_idx):
        call_count = [0]
        backtrack_count = [0]

        def solve_inner(idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] >= 0)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=self.height * self.width,
                )

            if idx >= self.height * self.width:
                if not _all_clues_satisfied(self.board, self.height, self.width, self.table):
                    return False
                return _white_cells_connected(self.board, self.height, self.width)

            r = idx // self.width
            c = idx % self.width
            clue = self.table[r][c]

            if clue > 0:
                # Numbered cell must be white
                self.board[r][c] = 0
                # Prune: if this clue's visibility already exceeds, fail
                vis = _visible_white_count_if_all_unknown_white(self.board, self.height, self.width, r, c)
                if vis > clue:
                    self.board[r][c] = -1
                    return False
                if solve_inner(idx + 1):
                    return True
                self.board[r][c] = -1
                backtrack_count[0] += 1
                return False

            # Try black first (if no H/V adjacent black)
            if not _has_adjacent_black_hv(self.board, self.height, self.width, r, c):
                self.board[r][c] = 1
                # Prune: if any clue is now fully determined with wrong count, fail
                clue_ok = True
                for rr in range(self.height):
                    for cc in range(self.width):
                        if self.table[rr][cc] > 0:
                            vis, determined = _clue_visible_and_determined(
                                self.board, self.height, self.width, rr, cc
                            )
                            if determined and vis != self.table[rr][cc]:
                                clue_ok = False
                                break
                    if not clue_ok:
                        break
                if clue_ok and solve_inner(idx + 1):
                    return True
                self.board[r][c] = -1
                backtrack_count[0] += 1

            # Try white
            self.board[r][c] = 0
            # Prune: any clue that sees this cell might exceed; check all clues
            ok = True
            for rr in range(self.height):
                for cc in range(self.width):
                    if self.table[rr][cc] > 0:
                        v = _visible_white_count_if_all_unknown_white(self.board, self.height, self.width, rr, cc)
                        if v > self.table[rr][cc]:
                            ok = False
                            break
                if not ok:
                    break
            if ok and solve_inner(idx + 1):
                return True
            self.board[r][c] = -1
            backtrack_count[0] += 1
            return False

        return solve_inner(cell_idx)

    def solve(self):
        """Solve the Kurodoko puzzle. Returns 2D grid with 0=white, 1=black."""
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = self._solve(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
