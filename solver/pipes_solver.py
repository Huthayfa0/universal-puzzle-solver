"""Pipes puzzle solver.

Rules:
- Rotate the tiles on the grid so all pipes are connected in a single group.
- Closed loops are not allowed (the network must be a tree).
- Tap/click a tile to rotate it 90° clockwise.

Tile types: 0=empty, 1=straight, 2=corner, 3=T, 4=cross.
Solution: grid of rotations (0, 1, 2, or 3) = number of 90° CW clicks per cell.
"""

from .solver import BaseSolver


# Directions: U, R, D, L (index 0..3)
_U, _R, _D, _L = 0, 1, 2, 3

# Base openings [U, R, D, L] for each tile type (before rotation).
# Type 0: empty; 1: straight U-D; 2: corner U-R; 3: T (U-R-D); 4: cross
_TILE_OPENINGS = [
    [0, 0, 0, 0],  # 0 empty
    [1, 0, 1, 0],  # 1 straight
    [1, 1, 0, 0],  # 2 corner
    [1, 1, 1, 0],  # 3 T
    [1, 1, 1, 1],  # 4 cross
]


def _rotate_openings(openings, rot):
    """Rotate openings by rot*90° clockwise. rot in 0..3."""
    for _ in range(rot):
        openings = [openings[_L], openings[_U], openings[_R], openings[_D]]
    return openings


def _get_openings(tile_type, rotation):
    """Return [U, R, D, L] (0/1) for this tile type and rotation."""
    if tile_type < 0 or tile_type >= len(_TILE_OPENINGS):
        return [0, 0, 0, 0]
    base = _TILE_OPENINGS[tile_type][:]
    return _rotate_openings(base, rotation)


# Neighbor deltas: up, right, down, left (so side k connects to (r+dr[k], c+dc[k]))
_D4 = [(-1, 0), (0, 1), (1, 0), (0, -1)]


def _connected_neighbors(height, width, table, rotations, r, c):
    """Yield (nr, nc) for cells that (r,c) is connected to (shared edge open on both)."""
    t = table[r][c]
    if t == 0:
        return
    openings = _get_openings(t, rotations[r][c])
    for side, (dr, dc) in enumerate(_D4):
        if not openings[side]:
            continue
        nr, nc = r + dr, c + dc
        if not (0 <= nr < height and 0 <= nc < width):
            continue
        nt = table[nr][nc]
        if nt == 0:
            continue
        # Neighbor's side opposite to ours (our U -> neighbor D, etc.)
        opp_side = (side + 2) % 4
        n_openings = _get_openings(nt, rotations[nr][nc])
        if n_openings[opp_side]:
            yield (nr, nc)


def _count_components_and_edges(height, width, table, rotations):
    """Return (number of connected components, total edge count) among non-empty cells."""
    visited = [[False] * width for _ in range(height)]
    total_edges = 0
    components = 0

    for r in range(height):
        for c in range(width):
            if table[r][c] == 0 or visited[r][c]:
                continue
            components += 1
            stack = [(r, c)]
            visited[r][c] = True
            while stack:
                i, j = stack.pop()
                for ni, nj in _connected_neighbors(height, width, table, rotations, i, j):
                    total_edges += 1  # count each edge once (from this cell's perspective we count each edge)
                    if not visited[ni][nj]:
                        visited[ni][nj] = True
                        stack.append((ni, nj))

    # We counted each edge twice (from both endpoints)
    total_edges //= 2
    return components, total_edges


def _count_cells(table):
    """Number of non-empty cells."""
    return sum(1 for row in table for c in row if c != 0)


def _is_valid_solution(height, width, table, rotations):
    """True if one connected component and no loop (tree: edges == cells - 1)."""
    n_cells = _count_cells(table)
    if n_cells == 0:
        return True
    components, edges = _count_components_and_edges(height, width, table, rotations)
    if components != 1:
        return False
    # Tree: edges == n_cells - 1
    return edges == n_cells - 1


def _max_rotations(tile_type):
    """Number of distinct rotations for this type (1, 2, or 4)."""
    if tile_type == 0:
        return 1
    if tile_type in (1, 2):  # straight has 2, corner has 4
        return 2 if tile_type == 1 else 4
    return 4  # T and cross


class PipesSolver(BaseSolver):
    """Solver for Pipes puzzles.

    Input: grid of tile types from TableTaskParser (0=empty, 1=straight, 2=corner, 3=T, 4=cross).
    Parser may store 0 as 2.
    Output: 2D grid of rotations (0, 1, 2, 3) = number of 90° CW clicks to apply per cell.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.table = self._normalize_table(info["table"])
        self.height = info["height"]
        self.width = info["width"]
        # rotations[r][c] in 0..3
        self.rotations = [[0] * self.width for _ in range(self.height)]
        self.cell_list = [
            (r, c) for r in range(self.height) for c in range(self.width)
            if self.table[r][c] != 0
        ]

    def _normalize_table(self, table):
        """Parser stores 0 as 2; ensure 0=empty, 1-4 = pipe types."""
        out = []
        for row in table:
            out_row = []
            for c in row:
                if c == 2 or (isinstance(c, str) and c in ("0", "W")):
                    out_row.append(0)
                elif isinstance(c, int) and 0 <= c <= 4:
                    out_row.append(0 if c == 0 else c)
                else:
                    out_row.append(0)
            out.append(out_row)
        return out

    def _solve(self, idx):
        """Backtrack over rotations. idx indexes self.cell_list."""
        if idx >= len(self.cell_list):
            return _is_valid_solution(self.height, self.width, self.table, self.rotations)

        r, c = self.cell_list[idx]
        t = self.table[r][c]
        max_r = _max_rotations(t)

        for rot in range(max_r):
            self.rotations[r][c] = rot
            if self._has_cycle_after(idx):
                continue
            if self._solve(idx + 1):
                return True
        return False

    def _has_cycle_after(self, last_idx):
        """Check if the graph formed by cells 0..last_idx (in cell_list) has a cycle."""
        # Build adjacency only for cells we've set so far
        placed = set(self.cell_list[i] for i in range(last_idx + 1))
        # Count edges and nodes in the induced subgraph
        nodes = 0
        edges = 0
        for (r, c) in placed:
            if self.table[r][c] == 0:
                continue
            nodes += 1
            for (nr, nc) in _connected_neighbors(
                self.height, self.width, self.table, self.rotations, r, c
            ):
                if (nr, nc) in placed:
                    edges += 1
        edges //= 2
        # Tree: edges <= nodes - 1. If edges >= nodes we have a cycle.
        return edges >= nodes and nodes > 0

    def solve(self):
        """Find rotations so all pipes are connected with no closed loop."""
        self._start_progress_tracking()
        try:
            if not self.cell_list:
                self._stop_progress_tracking()
                return self.rotations

            if self._solve(0):
                self._stop_progress_tracking()
                return self.rotations
            raise RuntimeError("Pipes solver: no solution found")
        finally:
            self._stop_progress_tracking()
