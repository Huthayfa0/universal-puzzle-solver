"""Tapa puzzle solver.

Rules:
- Shade some cells black so they form a single polyomino (all black cells connected orthogonally).
- No 2x2 black areas allowed.
- Clues in cells indicate the lengths of consecutive black blocks in the 8 neighboring cells.
- One number = one block of that length; multiple numbers = multiple blocks (at least one white between blocks).
- Blocks can appear in any order around the clue.
- Clue cells themselves are white (not shaded).
- Output: 0 = white, 1 = black. Submit: 1 = shade, 0 = skip.
"""

from collections import deque

from .solver import BaseSolver


# 4 directions for connectivity (orthogonal)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]

# 8 neighbors of a cell: row-by-row order (top-left to bottom-right)
# (-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)
_D8 = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def _normalize_clues(table, height, width):
    """Build clue grid: clues[r][c] = list of block lengths, or [] if no clue.
    Parser: 0 stored as 2; positive integer = one block of that length.
    Support list in cell for multi-block (e.g. [1,2] from custom parsing).
    """
    clues = []
    for r in range(height):
        row = []
        for c in range(width):
            v = table[r][c]
            if v == 2 or v == 0:
                row.append([])
            elif isinstance(v, list):
                row.append(list(v))
            elif isinstance(v, int) and v > 0:
                row.append([v])
            else:
                row.append([])
        clues.append(row)
    return clues


def _get_neighbor_states(board, cr, cc, height, width):
    """Return list of (r, c, state) for the 8 neighbors of (cr, cc) in order.
    state: -1 unknown, 0 white, 1 black. Only in-bounds neighbors included.
    """
    result = []
    for dr, dc in _D8:
        r, c = cr + dr, cc + dc
        if 0 <= r < height and 0 <= c < width:
            result.append((r, c, board[r][c]))
    return result


def _blocks_from_neighbors(neighbor_states):
    """Given list of (r, c, state) in order around a clue, return list of block lengths.
    Consecutive black (1) form a block; -1 (unknown) breaks a run (conservative).
    """
    blocks = []
    current = 0
    for _, _, s in neighbor_states:
        if s == 1:
            current += 1
        else:
            if current > 0:
                blocks.append(current)
            current = 0
    if current > 0:
        blocks.append(current)
    return blocks


def _clue_satisfied(clue_blocks, neighbor_states):
    """Check if the neighbor pattern can satisfy the clue.
    clue_blocks: sorted list of required block lengths.
    neighbor_states: list of (r, c, state) with state in {-1, 0, 1}.
    If any neighbor is unknown (-1), check feasibility: current blocks must be extendable to clue_blocks.
    """
    if not clue_blocks:
        # No black blocks allowed around this clue
        return all(s != 1 for _, _, s in neighbor_states)
    blocks = _blocks_from_neighbors(neighbor_states)
    total_black = sum(1 for _, _, s in neighbor_states if s == 1)
    has_unknown = any(s == -1 for _, _, s in neighbor_states)
    if not has_unknown:
        return sorted(blocks) == sorted(clue_blocks)
    # Partial: total blacks cannot exceed sum of clue blocks
    if total_black > sum(clue_blocks):
        return False
    # Current blocks (from consecutive 1s) must be extendable to match clue_blocks:
    # len(blocks) <= len(clue_blocks), and we can assign each current block to a required block (current <= required)
    needed = sorted(clue_blocks, reverse=True)
    got = sorted(blocks, reverse=True)
    if len(got) > len(needed):
        return False
    if sum(got) > sum(needed):
        return False
    for i, g in enumerate(got):
        if g > needed[i]:
            return False
    return True


def _has_2x2_black(board, r, c, height, width):
    """True if (r,c) is black and some 2x2 containing (r,c) is all black."""
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


def _black_connected(board, height, width):
    """True iff all black (1) cells form a single connected component (orthogonal)."""
    start = None
    black_count = 0
    for r in range(height):
        for c in range(width):
            if board[r][c] == 1:
                black_count += 1
                if start is None:
                    start = (r, c)
    if black_count <= 1:
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


def _all_clues_satisfied(board, clues, height, width):
    """True iff every clue cell's 8 neighbors satisfy its clue (no unknowns)."""
    for r in range(height):
        for c in range(width):
            if not clues[r][c]:
                continue
            neighbors = _get_neighbor_states(board, r, c, height, width)
            if any(s == -1 for _, _, s in neighbors):
                return False
            blocks = _blocks_from_neighbors(neighbors)
            if sorted(blocks) != sorted(clues[r][c]):
                return False
    return True


class TapaSolver(BaseSolver):
    """Solver for Tapa puzzles.

    Input: grid from TableTaskParser; 0/2 = no clue, positive = one block length (or list for multi-block).
    Clue cells are always white.
    Output: 2D grid with 0 = white, 1 = black. Submit: 1 = shade, 0 = skip.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.clues = _normalize_clues(info["table"], self.height, self.width)
        # board[r][c]: -1 unknown, 0 white, 1 black. Clue cells are fixed white.
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        for r in range(self.height):
            for c in range(self.width):
                if self.clues[r][c]:
                    self.board[r][c] = 0  # clue cells are white

    def _clue_ok_at(self, cr, cc):
        """True if the current neighbor pattern at clue (cr, cc) can still satisfy the clue."""
        neighbors = _get_neighbor_states(self.board, cr, cc, self.height, self.width)
        return _clue_satisfied(self.clues[cr][cc], neighbors)

    def _all_clues_ok(self):
        """True if every clue cell's neighborhood is still feasible."""
        for r in range(self.height):
            for c in range(self.width):
                if not self.clues[r][c]:
                    continue
                if not self._clue_ok_at(r, c):
                    return False
        return True

    def solve(self):
        """Solve the Tapa puzzle. Returns 2D grid with 0=white, 1=black."""
        # List cells to fill (non-clue, in row-major order)
        cells = []
        for r in range(self.height):
            for c in range(self.width):
                if self.board[r][c] == -1:
                    cells.append((r, c))
        n_cells = len(cells)
        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress(idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] >= 0)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=self.height * self.width,
                )

            if idx >= n_cells:
                if not _all_clues_satisfied(self.board, self.clues, self.height, self.width):
                    return False
                if not _black_connected(self.board, self.height, self.width):
                    return False
                return True

            r, c = cells[idx]

            # Option 1: black
            self.board[r][c] = 1
            if not _has_2x2_black(self.board, r, c, self.height, self.width) and self._all_clues_ok():
                if solve_with_progress(idx + 1):
                    return True
            self.board[r][c] = -1
            backtrack_count[0] += 1

            # Option 2: white
            self.board[r][c] = 0
            if self._all_clues_ok():
                if solve_with_progress(idx + 1):
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
