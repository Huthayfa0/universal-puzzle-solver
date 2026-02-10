"""Hashi (Bridges) puzzle solver.

Rules:
- Connect all islands (cells with numbers 1-8) into a single connected group with bridges.
- Bridges begin and end at distinct islands, run in a straight line (orthogonal only).
- Bridges must not cross each other or islands.
- At most two bridges connect any pair of islands.
- The number of bridges connected to each island must match the number on that island.
"""

from collections import deque

from .solver import BaseSolver


def _normalize_table(table):
    """Convert parser table: empty stored as 2 → 0, islands 1-8 unchanged."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _get_islands(table, height, width):
    """Return list of (r, c, value) for each island (value 1-8)."""
    islands = []
    for r in range(height):
        for c in range(width):
            v = table[r][c]
            if 1 <= v <= 8:
                islands.append((r, c, v))
    return islands


def _build_edges(islands, height, width):
    """Build list of possible edges between islands.
    Each edge: (island_i, island_j, 'H', r, c_lo, c_hi) or (i, j, 'V', c, r_lo, r_hi).
    Only same row/col with no other island in between.
    """
    n = len(islands)
    pos = {(islands[i][0], islands[i][1]): i for i in range(n)}
    edges = []

    # Horizontal: same row, consecutive columns with no island in between
    for i in range(n):
        r, c_i, _ = islands[i]
        for j in range(n):
            if i >= j:
                continue
            rj, c_j, _ = islands[j]
            if r != rj:
                continue
            c_lo, c_hi = min(c_i, c_j), max(c_i, c_j)
            # no other island in (c_lo, c_hi) in this row
            blocked = False
            for cc in range(c_lo + 1, c_hi):
                if (r, cc) in pos:
                    blocked = True
                    break
            if blocked:
                continue
            edges.append((i, j, "H", r, c_lo, c_hi))

    # Vertical: same column
    for i in range(n):
        r_i, c, _ = islands[i]
        for j in range(n):
            if i >= j:
                continue
            r_j, cj, _ = islands[j]
            if c != cj:
                continue
            r_lo, r_hi = min(r_i, r_j), max(r_i, r_j)
            blocked = False
            for rr in range(r_lo + 1, r_hi):
                if (rr, c) in pos:
                    blocked = True
                    break
            if blocked:
                continue
            edges.append((i, j, "V", c, r_lo, r_hi))

    return edges


def _segments_intersect(h, v):
    """h = ('H', r, c_lo, c_hi), v = ('V', c, r_lo, r_hi). True if they cross (interior)."""
    _, r, c_lo, c_hi = h
    _, c, r_lo, r_hi = v
    return r_lo < r < r_hi and c_lo < c < c_hi


def _edges_cross(ei, ej, edges_info, bridge_count):
    """Check if edge ei and ej (with bridge_count) cross. edges_info[i] = (i, j, 'H', r, c_lo, c_hi) or V."""
    if bridge_count[ei] == 0 or bridge_count[ej] == 0:
        return False
    hi = edges_info[ei]
    hj = edges_info[ej]
    if hi[2] == hj[2]:
        return False  # both H or both V: no crossing (parallel)
    if hi[2] == "H":
        h, v = hi, hj
    else:
        h, v = hj, hi
    return _segments_intersect(
        (h[2], h[3], h[4], h[5]),
        (v[2], v[3], v[4], v[5]),
    )


def _is_connected(n, edges_info, bridge_count):
    """True iff islands form one connected component using edges with bridge_count > 0."""
    adj = [[] for _ in range(n)]
    for idx, (i, j, *_) in enumerate(edges_info):
        if bridge_count[idx] > 0:
            adj[i].append(j)
            adj[j].append(i)
    visited = [False] * n
    q = deque([0])
    visited[0] = True
    while q:
        u = q.popleft()
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                q.append(v)
    return all(visited)


def _degree_ok(islands, edges_info, bridge_count, island_idx):
    """Current degree of island_idx and required value."""
    required = islands[island_idx][2]
    degree = 0
    for idx, (i, j, *_) in enumerate(edges_info):
        if bridge_count[idx] > 0:
            if i == island_idx or j == island_idx:
                degree += bridge_count[idx]
    return degree <= required, degree, required


def _can_exceed_degree(islands, edges_info, bridge_count, edge_idx, choice):
    """If we set edge edge_idx to choice, would any island exceed its required degree?"""
    i, j = edges_info[edge_idx][0], edges_info[edge_idx][1]
    # current degrees without this edge
    deg_i = sum(bridge_count[idx] for idx, (a, b, *_) in enumerate(edges_info) if (a == i or b == i) and idx != edge_idx)
    deg_j = sum(bridge_count[idx] for idx, (a, b, *_) in enumerate(edges_info) if (a == j or b == j) and idx != edge_idx)
    return (deg_i + choice <= islands[i][2]) and (deg_j + choice <= islands[j][2])


class HashiSolver(BaseSolver):
    """Solver for Hashi (Bridges) puzzles.

    Input: grid from TableTaskParser. Empty = 0 (stored as 2), islands = 1-8.
    Output: dict with "horizontal_bridges" (height x (width-1)) and "vertical_bridges" ((height-1) x width),
            values 0, 1, or 2.
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
        self.islands = _get_islands(self.table, self.height, self.width)
        self.edges = _build_edges(self.islands, self.height, self.width)
        # edge index -> (island_i, island_j, 'H', r, c_lo, c_hi) or ('V', c, r_lo, r_hi)
        self.edges_info = []
        for i, j, kind, a, b, c in self.edges:
            self.edges_info.append((i, j, kind, a, b, c))
        self.bridge_count = [0] * len(self.edges)  # current assignment

    def _any_crossing(self, edge_idx):
        """True if edge_idx crosses any already-assigned edge with bridge_count > 0."""
        for other in range(len(self.edges)):
            if other == edge_idx:
                continue
            if _edges_cross(edge_idx, other, self.edges_info, self.bridge_count):
                return True
        return False

    def _solve(self, edge_idx, call_count, backtrack_count):
        if edge_idx >= len(self.edges):
            if not _is_connected(len(self.islands), self.edges_info, self.bridge_count):
                return False
            # all degrees must match
            for i in range(len(self.islands)):
                _, deg, req = _degree_ok(self.islands, self.edges_info, self.bridge_count, i)
                if deg != req:
                    return False
            return True

        if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                edges_assigned=edge_idx,
                total_edges=len(self.edges),
            )

        call_count[0] += 1
        for choice in (0, 1, 2):
            if not _can_exceed_degree(self.islands, self.edges_info, self.bridge_count, edge_idx, choice):
                continue
            self.bridge_count[edge_idx] = choice
            if choice > 0 and self._any_crossing(edge_idx):
                self.bridge_count[edge_idx] = 0
                continue
            if self._solve(edge_idx + 1, call_count, backtrack_count):
                return True
            backtrack_count[0] += 1
            self.bridge_count[edge_idx] = 0
        return False

    def _build_bridge_grids(self):
        """From bridge_count, build horizontal_bridges and vertical_bridges 2D arrays."""
        # horizontal_bridges[r][c] = bridges between (r,c) and (r, c+1)
        horizontal_bridges = [[0] * (self.width - 1) for _ in range(self.height)]
        # vertical_bridges[r][c] = bridges between (r,c) and (r+1, c)
        vertical_bridges = [[0] * self.width for _ in range(self.height - 1)]

        for idx, (i, j, kind, a, b, c) in enumerate(self.edges_info):
            count = self.bridge_count[idx]
            if count == 0:
                continue
            if kind == "H":
                r = a
                c_lo, c_hi = b, c
                for cc in range(c_lo, c_hi):
                    horizontal_bridges[r][cc] += count
            else:
                col = a
                r_lo, r_hi = b, c
                for rr in range(r_lo, r_hi):
                    vertical_bridges[rr][col] += count

        return horizontal_bridges, vertical_bridges

    def solve(self):
        """Solve the Hashi puzzle. Returns dict with horizontal_bridges and vertical_bridges."""
        if len(self.islands) == 0:
            return {
                "horizontal_bridges": [[0] * (self.width - 1) for _ in range(self.height)],
                "vertical_bridges": [[0] * self.width for _ in range(self.height - 1)],
            }

        call_count = [0]
        backtrack_count = [0]
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = self._solve(0, call_count, backtrack_count)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        h_b, v_b = self._build_bridge_grids()
        return {"horizontal_bridges": h_b, "vertical_bridges": v_b}
