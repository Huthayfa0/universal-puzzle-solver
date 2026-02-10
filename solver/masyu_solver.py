"""Masyu puzzle solver.

Rules:
- Draw lines between adjacent dots to form a single loop (no crossings or branches).
- The loop passes through all black and white circles.
- White circles: the loop must pass through in a straight line, but must turn
  in the previous and/or next cell (at least one adjacent vertex on the path is a turn).
- Black circles: the loop must turn at the black circle, and travel straight
  through the next and the previous cell (both adjacent vertices on the path are straight).
"""

from .solver import BaseSolver

# Directions: (dr, dc) for down, right, up, left
_D4 = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def _adjacent_edges(r, c, height, width):
    """Yield all edges incident to dot (r, c) as ((r1,c1), (r2,c2)) with (r1,c1) < (r2,c2)."""
    for dr, dc in _D4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < height and 0 <= nc < width:
            a, b = (r, c), (nr, nc)
            if a > b:
                a, b = b, a
            yield (a, b)


def _edge_direction(a, b):
    """Return (dr, dc) from a to b."""
    return (b[0] - a[0], b[1] - a[1])


def _are_collinear(d1, d2):
    """True if directions d1 and d2 are opposite (same line, straight through)."""
    return d1[0] + d2[0] == 0 and d1[1] + d2[1] == 0


def _are_perpendicular(d1, d2):
    """True if directions d1 and d2 are perpendicular (turn)."""
    return d1[0] * d2[0] + d1[1] * d2[1] == 0


class MasyuSolver(BaseSolver):
    """Solver for Masyu puzzles.

    Input: dot grid (height x width) with table (0=empty, 1=white, 2=black).
    Output: dict with "horizontal_walls" (height x (width-1)) and
    "vertical_walls" ((height-1) x width), 1 = edge in loop, 0 = not.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.height = info["height"]
        self.width = info["width"]
        self.table = info["table"]  # 0=empty, 1=white, 2=black

        self.circles = []
        for r in range(self.height):
            for c in range(self.width):
                t = self.table[r][c]
                if t in (1, 2):
                    self.circles.append((r, c, t == 1))  # (r, c, is_white)

        self.h_edges = []
        self.v_edges = []
        for r in range(self.height):
            for c in range(self.width - 1):
                self.h_edges.append(((r, c), (r, c + 1)))
        for r in range(self.height - 1):
            for c in range(self.width):
                self.v_edges.append(((r, c), (r + 1, c)))

        self.all_edges = self.h_edges + self.v_edges
        self.edge_to_idx = {e: i for i, e in enumerate(self.all_edges)}
        self.n_h = len(self.h_edges)

    def _edges_incident(self, r, c):
        """Return list of edges (from all_edges) incident to dot (r,c)."""
        out = []
        for e in _adjacent_edges(r, c, self.height, self.width):
            if e in self.edge_to_idx:
                out.append(e)
        return out

    def _solution_to_used(self, used_set):
        """Convert set of edges to horizontal_walls and vertical_walls grids."""
        h_grid = [[0] * (self.width - 1) for _ in range(self.height)]
        v_grid = [[0] * self.width for _ in range(self.height - 1)]
        for (a, b) in used_set:
            r1, c1 = a
            r2, c2 = b
            if r1 == r2:
                c = min(c1, c2)
                h_grid[r1][c] = 1
            else:
                r = min(r1, r2)
                v_grid[r][c1] = 1
        return {"horizontal_walls": h_grid, "vertical_walls": v_grid}

    def _build_cycle_order(self, used_set):
        """From a set of edges that form a single cycle, return list of vertices in order (or None)."""
        if not used_set:
            return None
        adj = {}
        for (a, b) in used_set:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        for v in adj:
            if len(adj[v]) != 2:
                return None
        start = next(iter(used_set))[0]
        order = [start]
        prev = start
        cur = adj[start][0]
        while cur != start:
            order.append(cur)
            nexts = adj[cur]
            nxt = nexts[1] if nexts[0] == prev else nexts[0]
            prev, cur = cur, nxt
        if len(order) != len(adj):
            return None
        return order

    def _is_turn_at_vertex(self, v, adj):
        """True if at vertex v the two path edges form a turn (perpendicular)."""
        if v not in adj or len(adj[v]) != 2:
            return False
        a, b = adj[v][0], adj[v][1]
        d1 = _edge_direction(v, a)
        d2 = _edge_direction(v, b)
        return _are_perpendicular(d1, d2)

    def _is_straight_at_vertex(self, v, adj):
        """True if at vertex v the two path edges are collinear (straight through)."""
        if v not in adj or len(adj[v]) != 2:
            return False
        a, b = adj[v][0], adj[v][1]
        d1 = _edge_direction(v, a)
        d2 = _edge_direction(v, b)
        return _are_collinear(d1, d2)

    def _check_circle_constraints(self, order, used_set):
        """Check Masyu rules: white=straight through + turn at prev/next; black=turn + straight at prev/next."""
        if not order:
            return False
        adj = {}
        for (a, b) in used_set:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        # Build index of vertex -> position in cycle
        pos = {v: i for i, v in enumerate(order)}
        n = len(order)

        for (r, c, is_white) in self.circles:
            v = (r, c)
            if v not in adj or len(adj[v]) != 2:
                return False
            a, b = adj[v][0], adj[v][1]
            d1 = _edge_direction(v, a)
            d2 = _edge_direction(v, b)

            if is_white:
                # White: pass through in a straight line (collinear at this dot)
                if not _are_collinear(d1, d2):
                    return False
                # Must turn in previous and/or next cell: at least one neighbor on path is a turn
                i = pos[v]
                prev_v = order[(i - 1) % n]
                next_v = order[(i + 1) % n]
                turn_at_prev = self._is_turn_at_vertex(prev_v, adj)
                turn_at_next = self._is_turn_at_vertex(next_v, adj)
                if not (turn_at_prev or turn_at_next):
                    return False
            else:
                # Black: turn at this dot (perpendicular)
                if not _are_perpendicular(d1, d2):
                    return False
                # Must go straight through previous and next cell: both neighbors are straight
                i = pos[v]
                prev_v = order[(i - 1) % n]
                next_v = order[(i + 1) % n]
                if not self._is_straight_at_vertex(prev_v, adj):
                    return False
                if not self._is_straight_at_vertex(next_v, adj):
                    return False
        return True

    def _degree_at(self, used_set, r, c):
        return sum(1 for e in self._edges_incident(r, c) if e in used_set)

    def _solve(self, used_set, edge_idx, call_count, backtrack_count):
        """Backtrack: try adding edges. used_set is set of edges in the loop."""
        call_count[0] += 1
        if self.show_progress and self.progress_tracker and call_count[0] % 1000 == 0:
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                edges_used=len(used_set),
                total_edges=len(self.all_edges),
            )

        if edge_idx >= len(self.all_edges):
            order = self._build_cycle_order(used_set)
            if order is None:
                return False
            circle_verts = {(r, c) for r, c, _ in self.circles}
            if not circle_verts.issubset(set(order)):
                return False
            if self._check_circle_constraints(order, used_set):
                return True
            return False

        e = self.all_edges[edge_idx]
        a, b = e
        r1, c1 = a
        r2, c2 = b

        if self._solve(used_set, edge_idx + 1, call_count, backtrack_count):
            return True

        d1 = self._degree_at(used_set, r1, c1)
        d2 = self._degree_at(used_set, r2, c2)
        if d1 < 2 and d2 < 2:
            used_set.add(e)
            if self._solve(used_set, edge_idx + 1, call_count, backtrack_count):
                return True
            used_set.discard(e)
            backtrack_count[0] += 1

        return False

    def solve(self):
        """Solve the Masyu puzzle. Returns dict with horizontal_walls and vertical_walls."""
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        call_count = [0]
        backtrack_count = [0]
        used_set = set()
        try:
            ok = self._solve(used_set, 0, call_count, backtrack_count)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return self._solution_to_used(used_set)
