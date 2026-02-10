"""Slant (Gokigen Naname) puzzle solver.

Rules:
- Place a diagonal line in EVERY cell: either \ (backslash) or / (forward slash).
- Numbers at grid points show how many diagonal lines meet at that point (0, 1, 2, 3, or 4).
- The lines must NOT form a loop (the diagonal graph must be acyclic).
"""

from .solver import BaseSolver


def _normalize_clue(parsed_value):
    """Convert parser table value to clue: 0-4 or -1 for no constraint.
    TableTaskParser stores digit 0 as 2; digits 1,2,3,4 as 1,2,3,4.
    """
    if parsed_value in (1, 3, 4):
        return parsed_value
    if parsed_value == 2:
        return 0  # parser stores digit 0 as 2
    return -1  # empty / no constraint


def _diagonal_endpoints(i, j, slant):
    """Return the two grid points connected by the diagonal in cell (i, j).
    slant: 0 = backslash \\ (connects NW-SE), 1 = forward slash / (connects NE-SW).
    Points are (row, col) with row in 0..H, col in 0..W.
    """
    if slant == 0:
        return ((i, j), (i + 1, j + 1))
    return ((i, j + 1), (i + 1, j))


def _point_incident_cells(r, c, H, W):
    """Return list of (cell_i, cell_j, slant) that have a diagonal incident to point (r, c)."""
    out = []
    # Cell (r-1, c-1) with \ has endpoint (r, c)
    if r >= 1 and c >= 1:
        out.append((r - 1, c - 1, 0))
    # Cell (r-1, c) with / has endpoint (r, c)
    if r >= 1 and c < W:
        out.append((r - 1, c, 1))
    # Cell (r, c-1) with / has endpoint (r, c)
    if r < H and c >= 1:
        out.append((r, c - 1, 1))
    # Cell (r, c) with \ has endpoint (r, c)
    if r < H and c < W:
        out.append((r, c, 0))
    return out


class UnionFind:
    """Disjoint set to detect cycles: if two endpoints of an edge are in the same set, adding it would form a cycle."""

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False  # would form cycle
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True


class SlantSolver(BaseSolver):
    """Solver for Slant (Gokigen Naname) puzzles.

    Input: point_clues (H+1) x (W+1) with values 0-4 or -1 (no constraint).
    Board: H x W cells, each 0 = \\ or 1 = /.
    Output: 2D board of 0/1 for TableSubmitter.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.H = info["height"]
        self.W = info["width"]
        # Point clues: (H+1) x (W+1). Build from info["table"] if present (parser may give (H+1)x(W+1) table).
        table = info.get("table", [])
        if table:
            self.point_clues = []
            for r in range(self.H + 1):
                row = []
                for c in range(self.W + 1):
                    row.append(_normalize_clue(table[r][c]) if isinstance(table[r][c], int) else -1)
                self.point_clues.append(row)
        else:
            self.point_clues = [[-1] * (self.W + 1) for _ in range(self.H + 1)]

        self.board = [[-1] * self.W for _ in range(self.H)]  # -1 = unset, 0 = \, 1 = /
        self.num_points = (self.H + 1) * (self.W + 1)

    def _point_to_idx(self, r, c):
        return r * (self.W + 1) + c

    def _count_at_point(self, r, c):
        """Number of diagonals currently incident to point (r, c)."""
        count = 0
        for i, j, slant in _point_incident_cells(r, c, self.H, self.W):
            if self.board[i][j] == slant:
                count += 1
        return count

    def _solve(self, cell_idx, uf, call_count, backtrack_count):
        call_count[0] += 1
        if call_count[0] % 5000 == 0 and self.show_progress and self.progress_tracker:
            filled = sum(1 for i in range(self.H) for j in range(self.W) if self.board[i][j] >= 0)
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                cells_filled=filled,
                total_cells=self.H * self.W,
            )

        if cell_idx >= self.H * self.W:
            # Verify all point clues
            for r in range(self.H + 1):
                for c in range(self.W + 1):
                    clue = self.point_clues[r][c]
                    if clue >= 0 and self._count_at_point(r, c) != clue:
                        return False
            return True

        i = cell_idx // self.W
        j = cell_idx % self.W

        for slant in (0, 1):
            a, b = _diagonal_endpoints(i, j, slant)
            ia, ib = self._point_to_idx(a[0], a[1]), self._point_to_idx(b[0], b[1])
            uf_copy = UnionFind(self.num_points)
            uf_copy.parent = uf.parent[:]
            uf_copy.rank = uf.rank[:]
            if not uf_copy.union(ia, ib):
                continue

            # Check point clues not exceeded
            ok = True
            for r, c in (a, b):
                clue = self.point_clues[r][c]
                if clue >= 0:
                    count = self._count_at_point(r, c) + 1
                    if count > clue:
                        ok = False
                        break
            if not ok:
                continue

            self.board[i][j] = slant
            if self._solve(cell_idx + 1, uf_copy, call_count, backtrack_count):
                return True

            self.board[i][j] = -1
            backtrack_count[0] += 1

        return False

    def solve(self):
        """Solve the Slant puzzle. Returns H×W grid: 0 = \\, 1 = /."""
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        call_count = [0]
        backtrack_count = [0]
        uf = UnionFind(self.num_points)
        try:
            ok = self._solve(0, uf, call_count, backtrack_count)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [row[:] for row in self.board]
