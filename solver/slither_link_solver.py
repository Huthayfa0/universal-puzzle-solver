"""Slither Link puzzle solver.

Rules:
- Draw lines between adjacent dots to form a single loop without crossings or branches.
- The numbers in cells indicate how many of the four edges of that cell are part of the loop (0, 1, 2, 3, or 4).
"""

from .solver import BaseSolver

# Directions for adjacent dots: down, right, up, left
_D4 = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def _normalize_clue(parsed_value):
    """Convert parser table value to clue: 0-4 or -1 for no constraint.
    Parser stores digit 0 as 2; digits 1,2,3,4 as 1,2,3,4. So 2 can mean 0 or 2.
    We treat 2 as 0 (zero lines) to match parser convention; sites may use
    a different encoding for digit 2 (e.g. letter).
    """
    if parsed_value in (1, 3, 4):
        return parsed_value
    if parsed_value == 2:
        return 0  # Parser stores digit 0 as 2
    return -1  # Empty / no constraint


def _edges_around_cell(i, j):
    """Return the four edges (as ((r1,c1),(r2,c2))) around cell (i, j).
    Cell (i,j) has top, right, bottom, left edges.
    """
    return [
        ((i, j), (i, j + 1)),      # top
        ((i, j + 1), (i + 1, j + 1)),  # right
        ((i + 1, j), (i + 1, j + 1)),  # bottom
        ((i, j), (i + 1, j)),       # left
    ]


def _cells_for_edge(a, b, H, W):
    """Return list of cell (i, j) that contain edge (a, b). Each edge is in 1 or 2 cells."""
    r1, c1 = a
    r2, c2 = b
    cells = []
    if r1 == r2:
        # Horizontal edge (r, c)-(r, c+1)
        r, c = r1, min(c1, c2)
        if r < H:
            cells.append((r, c))
        if r > 0:
            cells.append((r - 1, c))
    else:
        # Vertical edge (r, c)-(r+1, c)
        r, c = min(r1, r2), c1
        if c < W:
            cells.append((r, c))
        if c > 0:
            cells.append((r, c - 1))
    return cells


class SlitherLinkSolver(BaseSolver):
    """Solver for Slither Link (Fences / Takegaki) puzzles.

    Input: table (height x width) of clues 0-4; parser stores 0 as 2, empty as -1.
    Output: dict with "horizontal_walls" ((height+1) x width) and
    "vertical_walls" (height x (width+1)), 1 = edge in loop, 0 = not.
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
        self.table = info["table"]
        # Clues: 0-4 or -1 for no constraint
        self.clues = []
        for r in range(self.H):
            row = []
            for c in range(self.W):
                row.append(_normalize_clue(self.table[r][c]))
            self.clues.append(row)

        # Build edge list: dots are (r, c) for r in 0..H, c in 0..W
        self.h_edges = []
        for r in range(self.H + 1):
            for c in range(self.W):
                self.h_edges.append(((r, c), (r, c + 1)))
        self.v_edges = []
        for r in range(self.H):
            for c in range(self.W + 1):
                self.v_edges.append(((r, c), (r + 1, c)))
        self.all_edges = self.h_edges + self.v_edges
        self.edge_to_idx = {e: i for i, e in enumerate(self.all_edges)}
        self.n_h = len(self.h_edges)

        # For each cell (i,j), list of edge indices
        self.cell_edges = []
        for i in range(self.H):
            for j in range(self.W):
                es = _edges_around_cell(i, j)
                self.cell_edges.append([self.edge_to_idx[e] for e in es])
        self.cell_edges_flat = self.cell_edges  # (i,j) -> cell_edges[i*W+j]

    def _edges_incident(self, r, c):
        """Return list of edges (from all_edges) incident to dot (r, c)."""
        out = []
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr <= self.H and 0 <= nc <= self.W:
                a, b = (r, c), (nr, nc)
                if a > b:
                    a, b = b, a
                e = (a, b)
                if e in self.edge_to_idx:
                    out.append(e)
        return out

    def _degree_at(self, used_set, r, c):
        return sum(1 for e in self._edges_incident(r, c) if e in used_set)

    def _count_cell_edges(self, used_set, i, j):
        """Number of edges in used_set that belong to cell (i, j)."""
        idx = i * self.W + j
        return sum(1 for ei in self.cell_edges_flat[idx] if self.all_edges[ei] in used_set)

    def _is_single_cycle(self, used_set):
        """Check that used_set forms a single cycle (one loop, no branches)."""
        if not used_set:
            return False
        adj = {}
        for (a, b) in used_set:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        for v in adj:
            if len(adj[v]) != 2:
                return False
        # Check connected: one component
        start = next(iter(used_set))[0]
        visited = {start}
        stack = [start]
        while stack:
            v = stack.pop()
            for u in adj[v]:
                if u not in visited:
                    visited.add(u)
                    stack.append(u)
        return len(visited) == len(adj)

    def _solution_to_walls(self, used_set):
        """Convert set of edges to horizontal_walls and vertical_walls for submitter."""
        # horizontal_walls: (H+1) x W
        h_grid = [[0] * self.W for _ in range(self.H + 1)]
        for (a, b) in used_set:
            r1, c1 = a
            r2, c2 = b
            if r1 == r2:
                c = min(c1, c2)
                h_grid[r1][c] = 1
        # vertical_walls: H x (W+1)
        v_grid = [[0] * (self.W + 1) for _ in range(self.H)]
        for (a, b) in used_set:
            r1, c1 = a
            r2, c2 = b
            if r1 != r2:
                r = min(r1, r2)
                v_grid[r][c1] = 1
        return {"horizontal_walls": h_grid, "vertical_walls": v_grid}

    def _solve(self, used_set, edge_idx, call_count, backtrack_count):
        """Backtrack: try including or excluding each edge."""
        call_count[0] += 1
        if self.show_progress and self.progress_tracker and call_count[0] % 5000 == 0:
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                edges_used=len(used_set),
                total_edges=len(self.all_edges),
            )

        if edge_idx >= len(self.all_edges):
            for i in range(self.H):
                for j in range(self.W):
                    clue = self.clues[i][j]
                    if clue >= 0 and self._count_cell_edges(used_set, i, j) != clue:
                        return False
            if self._is_single_cycle(used_set):
                return True
            return False

        # Early prune: if any cell has all 4 edges decided and count != clue, invalid
        for i in range(self.H):
            for j in range(self.W):
                clue = self.clues[i][j]
                if clue >= 0:
                    idx = i * self.W + j
                    if all(ei < edge_idx for ei in self.cell_edges_flat[idx]):
                        if self._count_cell_edges(used_set, i, j) != clue:
                            return False

        e = self.all_edges[edge_idx]
        a, b = e
        r1, c1 = a
        r2, c2 = b

        # Option 1: do not use this edge
        if self._solve(used_set, edge_idx + 1, call_count, backtrack_count):
            return True

        # Option 2: use this edge (if allowed)
        d1 = self._degree_at(used_set, r1, c1)
        d2 = self._degree_at(used_set, r2, c2)
        if d1 >= 2 or d2 >= 2:
            return False

        # Check cell constraints for cells that contain this edge
        cells_touched = _cells_for_edge(a, b, self.H, self.W)
        can_add = True
        for i, j in cells_touched:
            clue = self.clues[i][j]
            if clue >= 0:
                count = self._count_cell_edges(used_set, i, j)
                if count >= clue:
                    can_add = False
                    break
        if not can_add:
            return False

        used_set.add(e)

        # After adding, no cell may exceed its clue
        for i, j in cells_touched:
            clue = self.clues[i][j]
            if clue >= 0 and self._count_cell_edges(used_set, i, j) > clue:
                used_set.discard(e)
                return False

        if self._solve(used_set, edge_idx + 1, call_count, backtrack_count):
            return True

        used_set.discard(e)
        backtrack_count[0] += 1
        return False

    def solve(self):
        """Solve the Slither Link puzzle. Returns dict with horizontal_walls and vertical_walls."""
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
        return self._solution_to_walls(used_set)
