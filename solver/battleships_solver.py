"""Battleships puzzle solver.

Rules:
- Find the location of battleships (straight lines of consecutive black cells).
- Some cells may be pre-revealed (ship or water).
- Fleet: given counts per ship size (e.g. 1×4, 2×3, 1×2).
- Two battleships cannot touch (even diagonally).
- Row and column numbers show how many ship cells in that row/column.
"""

from .solver import BaseSolver


# Cell states: 0 = water, 1 = ship, -1 = unknown
WATER = 0
SHIP = 1
UNKNOWN = -1

# 4 directions (same ship); diagonals = no-touch
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]
_DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _normalize_cell(value):
    """Map parser output (W/B/0/1) to WATER, SHIP, or UNKNOWN. W/0 = unknown (to fill), B/1 = given ship."""
    if value in ("B", "b", 1):
        return SHIP
    if value in ("W", "w", 0):
        return UNKNOWN
    return UNKNOWN


class BattleshipsSolver(BaseSolver):
    """Solver for Battleships puzzles.

    Input: table (W/B/empty), horizontal_borders (row counts), vertical_borders (col counts), fleet (ship sizes).
    Output: 2D grid with 0 = water, 1 = ship.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.row_counts = info.get("horizontal_borders", [])
        self.col_counts = info.get("vertical_borders", [])
        self.fleet = list(info.get("fleet", []))
        self.fleet.sort(reverse=True)

        raw = info.get("table", [])
        self.board = [[UNKNOWN for _ in range(self.width)] for _ in range(self.height)]
        for i in range(self.height):
            for j in range(self.width):
                if i < len(raw) and j < len(raw[i]):
                    self.board[i][j] = _normalize_cell(raw[i][j])

        self.total_ship_cells = sum(self.row_counts) if self.row_counts else sum(self.col_counts)
        if not self.fleet and self.total_ship_cells:
            self._infer_fleet()

    def _infer_fleet(self):
        """Infer fleet from total ship cells (common configurations)."""
        t = self.total_ship_cells
        if t == 20:
            self.fleet = [4, 3, 3, 2]
        elif t == 14:
            self.fleet = [4, 3, 2, 2]
        elif t == 12:
            self.fleet = [4, 3, 2]
        elif t == 10:
            self.fleet = [3, 2, 2]
        elif t == 8:
            self.fleet = [3, 2]
        elif t == 6:
            self.fleet = [2, 2]
        else:
            self.fleet = []

    def _row_count(self, r):
        return sum(1 for c in range(self.width) if self.board[r][c] == SHIP)

    def _col_count(self, c):
        return sum(1 for r in range(self.height) if self.board[r][c] == SHIP)

    def _row_unknown(self, r):
        return sum(1 for c in range(self.width) if self.board[r][c] == UNKNOWN)

    def _col_unknown(self, c):
        return sum(1 for r in range(self.height) if self.board[r][c] == UNKNOWN)

    def _has_diagonal_ship(self, r, c):
        """True if any diagonal neighbor is ship (different ship cannot touch diagonally)."""
        for dr, dc in _DIAG:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.board[nr][nc] == SHIP:
                return True
        return False

    def _can_extend_ship(self, r, c):
        """True if (r,c) can be ship: no diagonal ship; 4-neighbor ships must be colinear (same row or same col)."""
        if self._has_diagonal_ship(r, c):
            return False
        four_neighbors = [
            (r + dr, c + dc) for dr, dc in _D4
            if 0 <= r + dr < self.height and 0 <= c + dc < self.width and self.board[r + dr][c + dc] == SHIP
        ]
        if not four_neighbors:
            return True
        rows = {nr for nr, _ in four_neighbors}
        cols = {nc for _, nc in four_neighbors}
        return len(rows) == 1 or len(cols) == 1


    def _get_ship_segments(self):
        """Return list of connected ship segments (each segment = set of (r,c))."""
        seen = set()
        segments = []
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] != SHIP or (i, j) in seen:
                    continue
                seg = set()
                stack = [(i, j)]
                while stack:
                    r, c = stack.pop()
                    if (r, c) in seg:
                        continue
                    seg.add((r, c))
                    seen.add((r, c))
                    for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.height and 0 <= nc < self.width and self.board[nr][nc] == SHIP:
                            stack.append((nr, nc))
                segments.append(seg)
        return segments

    def _segments_are_valid_ships(self, segments):
        """Check each segment is a straight line and lengths match fleet (multiset)."""
        lengths = []
        for seg in segments:
            pts = list(seg)
            if not pts:
                continue
            r0, c0 = pts[0]
            rows = {r for r, c in pts}
            cols = {c for r, c in pts}
            if len(rows) == 1:
                length = len(cols)
            elif len(cols) == 1:
                length = len(rows)
            else:
                return False
            lengths.append(length)
        lengths.sort(reverse=True)
        return lengths == self.fleet

    def _all_counts_met(self):
        for r in range(self.height):
            if self.row_counts[r] != self._row_count(r):
                return False
        for c in range(self.width):
            if self.col_counts[c] != self._col_count(c):
                return False
        return True

    def _solve(self, cell_idx, call_count=None):
        if call_count is not None:
            call_count[0] += 1
            if call_count[0] % 500 == 0 and self.progress_tracker:
                filled = sum(
                    1 for r in range(self.height) for c in range(self.width)
                    if self.board[r][c] != UNKNOWN
                )
                self._update_progress(
                    call_count=call_count[0],
                    cells_filled=filled,
                    total_cells=self.height * self.width,
                )
        if cell_idx >= self.height * self.width:
            if not self._all_counts_met():
                return False
            segments = self._get_ship_segments()
            return self._segments_are_valid_ships(segments)

        r = cell_idx // self.width
        c = cell_idx % self.width
        if self.board[r][c] != UNKNOWN:
            return self._solve(cell_idx + 1, call_count)

        target_row = self.row_counts[r] if r < len(self.row_counts) else 0
        target_col = self.col_counts[c] if c < len(self.col_counts) else 0
        row_has = self._row_count(r)
        col_has = self._col_count(c)
        row_unknown = self._row_unknown(r)
        col_unknown = self._col_unknown(c)

        # Try ship (no diagonal ship; 4-neighbor ships must be colinear)
        if row_has < target_row and col_has < target_col and self._can_extend_ship(r, c):
            self.board[r][c] = SHIP
            if self._solve(cell_idx + 1, call_count):
                return True
            self.board[r][c] = UNKNOWN

        # Try water
        need_row = target_row - row_has
        need_col = target_col - col_has
        if need_row <= row_unknown - 1 and need_col <= col_unknown - 1:
            self.board[r][c] = WATER
            if self._solve(cell_idx + 1, call_count):
                return True
            self.board[r][c] = UNKNOWN

        return False

    def solve(self):
        """Solve the Battleships puzzle. Returns 2D grid with 0 = water, 1 = ship."""
        if not self.fleet:
            return None
        if sum(self.fleet) != self.total_ship_cells:
            return None

        call_count = [0] if (self.show_progress and self.progress_tracker) else None
        if call_count is not None:
            self._start_progress_tracking()
        try:
            ok = self._solve(0, call_count)
        finally:
            if call_count is not None:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[1 if self.board[r][c] == SHIP else 0 for c in range(self.width)] for r in range(self.height)]
