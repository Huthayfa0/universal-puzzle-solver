"""LITS puzzle solver.

Rules:
- Place exactly one tetromino (L, I, T, or S) in each region.
- Two tetrominoes of the same type cannot touch horizontally or vertically (rotations/reflections count as matching).
- All shaded cells must form a single connected area (4-adjacency).
- No 2x2 shaded area is allowed.
"""

from collections import deque

from .solver import BaseSolver


# 4 directions: right, down, left, up
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]

# Tetromino type ids: L=0, I=1, T=2, S=3 (O is not used)
TYPE_L, TYPE_I, TYPE_T, TYPE_S = 0, 1, 2, 3


def _normalize_shape(cells):
    """Normalize shape so min row and min col are 0. cells = list of (r, c)."""
    if not cells:
        return []
    min_r = min(c[0] for c in cells)
    min_c = min(c[1] for c in cells)
    return tuple(sorted((r - min_r, c - min_c) for r, c in cells))


def _rotate_90(cells):
    """Rotate 90° clockwise: (r, c) -> (c, -r)."""
    return [(-c, r) for r, c in cells]


def _reflect_h(cells):
    """Reflect over horizontal axis: (r, c) -> (r, -c)."""
    return [(r, -c) for r, c in cells]


def _all_isometries(cells):
    """Return set of all 8 isometries (4 rotations × 2 reflections) normalized."""
    seen = set()
    result = []
    current = list(cells)
    for _ in range(4):
        n = _normalize_shape(current)
        if n not in seen:
            seen.add(n)
            result.append(n)
        current = _rotate_90(current)
    current = _reflect_h(list(cells))
    for _ in range(4):
        n = _normalize_shape(current)
        if n not in seen:
            seen.add(n)
            result.append(n)
        current = _rotate_90(current)
    return result


# Canonical tetromino shapes (each is list of 4 (r, c)); O is excluded.
_CANONICAL = {
    TYPE_L: [(0, 0), (1, 0), (2, 0), (2, 1)],
    TYPE_I: [(0, 0), (0, 1), (0, 2), (0, 3)],
    TYPE_T: [(0, 0), (0, 1), (0, 2), (1, 1)],
    TYPE_S: [(0, 1), (0, 2), (1, 0), (1, 1)],  # S shape
}
# Z shape is same type as S
_CANONICAL_Z = [(0, 0), (0, 1), (1, 1), (1, 2)]


def _build_tetromino_db():
    """Build for each type_id a list of normalized shapes (each tuple of 4 (r,c))."""
    db = {}
    for tid, cells in _CANONICAL.items():
        shapes = _all_isometries(cells)
        db[tid] = shapes
    # Add Z isometries to S (same type)
    for shape in _all_isometries(_CANONICAL_Z):
        if shape not in db[TYPE_S]:
            db[TYPE_S].append(shape)
    return db


_TETROMINO_DB = _build_tetromino_db()


def _shaded_connected(board, height, width):
    """Return True iff all shaded (1) cells form a single connected component."""
    shaded = []
    for r in range(height):
        for c in range(width):
            if board[r][c] == 1:
                shaded.append((r, c))
    if len(shaded) <= 1:
        return True
    visited = {shaded[0]}
    q = deque([shaded[0]])
    while q:
        r, c = q.popleft()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and board[nr][nc] == 1:
                cell = (nr, nc)
                if cell not in visited:
                    visited.add(cell)
                    q.append(cell)
    return len(visited) == len(shaded)


def _has_2x2(board, height, width, cells_to_check=None):
    """Return True if there is any 2x2 block of shaded cells. If cells_to_check is provided, only check 2x2 that include any of those."""
    if cells_to_check is not None:
        for r, c in cells_to_check:
            for dr in (0, -1):
                for dc in (0, -1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < height - 1 and 0 <= cc < width - 1:
                        if (board[rr][cc] == 1 and board[rr][cc + 1] == 1 and
                                board[rr + 1][cc] == 1 and board[rr + 1][cc + 1] == 1):
                            return True
        return False
    for r in range(height - 1):
        for c in range(width - 1):
            if (board[r][c] == 1 and board[r][c + 1] == 1 and
                    board[r + 1][c] == 1 and board[r + 1][c + 1] == 1):
                return True
    return False


def _cells_adjacent_to(cells):
    """Return set of cells that are 4-adjacent to any cell in cells."""
    out = set()
    for r, c in cells:
        for dr, dc in _D4:
            out.add((r + dr, c + dc))
    return out


class LitsSolver(BaseSolver):
    """Solver for LITS puzzles.

    Uses regions (boxes) from BoxesTaskParser.
    Board: 0 = unshaded, 1 = shaded. Solution is 2D grid of 0/1.
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
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.num_regions = len(self.boxes)
        self._region_cells = [set(box) for box in self.boxes]

    def _list_placements(self, region_id):
        """Yield (type_id, cells_set) for every valid tetromino placement in the region."""
        region_set = self._region_cells[region_id]
        for type_id, shapes in _TETROMINO_DB.items():
            for shape in shapes:
                # Try every anchor (r0, c0) so that (r0+dr, c0+dc) are in grid
                max_dr = max(s[0] for s in shape)
                max_dc = max(s[1] for s in shape)
                for r0 in range(self.height - max_dr):
                    for c0 in range(self.width - max_dc):
                        cells = [(r0 + dr, c0 + dc) for dr, dc in shape]
                        if all(c in region_set for c in cells):
                            yield type_id, set(cells)

    def _same_type_touches(self, new_cells, new_type, placed_by_type):
        """True if new_cells (type new_type) touches any same-type placement. placed_by_type[type_id] = set of cells (all 4) for each placed tetromino of that type."""
        if new_type not in placed_by_type:
            return False
        adj = _cells_adjacent_to(new_cells)
        for other_cells in placed_by_type[new_type]:
            if other_cells & adj:  # any cell of other is adjacent to any of new
                return True
        return False

    def solve(self):
        """Solve the LITS puzzle. Returns 2D board with 0=unshaded, 1=shaded."""
        # Order regions (e.g. by size) for more deterministic backtracking
        region_order = list(range(self.num_regions))
        region_order.sort(key=lambda r: (len(self.boxes[r]), r))

        # placed_by_type[type_id] = list of sets of 4 cells (each set is one tetromino)
        placed_by_type = {TYPE_L: [], TYPE_I: [], TYPE_T: [], TYPE_S: []}
        call_count = [0]
        backtrack_count = [0]

        def solve_rec(region_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                shaded = sum(1 for i in range(self.height) for j in range(self.width) if self.board[i][j] == 1)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=shaded,
                    total_cells=4 * self.num_regions,
                )

            if region_idx >= self.num_regions:
                return _shaded_connected(self.board, self.height, self.width)

            rid = region_order[region_idx]
            for type_id, cells in self._list_placements(rid):
                if self._same_type_touches(cells, type_id, placed_by_type):
                    continue
                # Check 2x2: add these 4 cells and see if any 2x2 appears
                for r, c in cells:
                    self.board[r][c] = 1
                if _has_2x2(self.board, self.height, self.width, cells):
                    for r, c in cells:
                        self.board[r][c] = 0
                    continue
                placed_by_type[type_id].append(cells)
                if solve_rec(region_idx + 1):
                    return True
                placed_by_type[type_id].pop()
                for r, c in cells:
                    self.board[r][c] = 0
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_rec(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [row[:] for row in self.board]
