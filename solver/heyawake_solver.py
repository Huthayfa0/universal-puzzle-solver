"""Heyawake puzzle solver.

Rules:
- Regions with a number must contain exactly that many black cells.
- Two black cells cannot be adjacent horizontally or vertically.
- A straight (orthogonal) line of connected white cells cannot span more than 2 regions.
- All white cells must be connected in a single group.
"""

from collections import deque

from .solver import BaseSolver


_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _white_run_region_count(boxes_table, board, r, c, dr, dc, height, width):
    """Return the number of distinct regions in the maximal white run through (r,c) in direction (dr,dc)."""
    if board[r][c] != 0:
        return 0
    regions = set()
    # walk one way
    i, j = r, c
    while 0 <= i < height and 0 <= j < width and board[i][j] == 0:
        regions.add(boxes_table[i][j])
        i += dr
        j += dc
    # walk the other way
    i, j = r - dr, c - dc
    while 0 <= i < height and 0 <= j < width and board[i][j] == 0:
        regions.add(boxes_table[i][j])
        i -= dr
        j -= dc
    return len(regions)


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


class HeyawakeSolver(BaseSolver):
    """Solver for Heyawake puzzles.

    Uses regions (boxes) and optional per-region numbers from CombinedTaskParser
    (BoxesTaskParser + TableTaskParser). Board: 0 = white, 1 = black.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        # -1 = no constraint; otherwise required number of black cells in that region
        self._build_region_numbers(info)
        # -1 = unassigned, 0 = white, 1 = black
        self.board = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        self.num_regions = len(self.boxes)

    def _build_region_numbers(self, info):
        """Build region_numbers[rid] from info['table'] (clue grid). Parser may store 0 as 2."""
        table = info.get("table", [])
        self.region_numbers = []
        for cells in self.boxes:
            if not table:
                self.region_numbers.append(-1)
                continue
            vals = []
            for i, j in cells:
                if 0 <= i < len(table) and 0 <= j < len(table[0]):
                    v = table[i][j]
                    if v == 2:  # parser stores 0 as 2
                        v = 0
                    vals.append(v)
            max_val = max(vals) if vals else 0
            self.region_numbers.append(max_val if max_val > 0 else -1)

    def _black_count_per_region(self):
        """Return list of current black counts per region."""
        counts = [0] * self.num_regions
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 1:
                    counts[self.boxes_table[i][j]] += 1
        return counts

    def _has_adjacent_black(self, r, c, exclude=None):
        """True if any 4-neighbor of (r,c) is black (1), optionally excluding a cell."""
        exclude = exclude or set()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if (nr, nc) not in exclude and self.board[nr][nc] == 1:
                    return True
        return False

    def _white_line_ok(self, r, c):
        """Check that the white run through (r,c) horizontally and vertically each span at most 2 regions."""
        h = _white_run_region_count(
            self.boxes_table, self.board, r, c, 0, 1, self.height, self.width
        )
        if h > 2:
            return False
        v = _white_run_region_count(
            self.boxes_table, self.board, r, c, 1, 0, self.height, self.width
        )
        return v <= 2

    def solve(self):
        """Solve the Heyawake puzzle. Returns 2D board with 0=white, 1=black."""
        call_count = [0]
        backtrack_count = [0]
        n_cells = self.height * self.width

        def solve_with_progress(cell_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(
                    1 for r in range(self.height) for c in range(self.width) if self.board[r][c] >= 0
                )
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=n_cells,
                )

            if cell_idx >= n_cells:
                counts = self._black_count_per_region()
                for rid, required in enumerate(self.region_numbers):
                    if required >= 0 and counts[rid] != required:
                        return False
                return _white_cells_connected(self.board, self.height, self.width)

            r = cell_idx // self.width
            c = cell_idx % self.width
            rid = self.boxes_table[r][c]
            required = self.region_numbers[rid]
            counts = self._black_count_per_region()

            # Option 1: place black
            if not self._has_adjacent_black(r, c):
                if required < 0 or counts[rid] < required:
                    self.board[r][c] = 1
                    if solve_with_progress(cell_idx + 1):
                        return True
                    self.board[r][c] = -1
                    backtrack_count[0] += 1

            # Option 2: place white
            self.board[r][c] = 0
            if self._white_line_ok(r, c):
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
