"""Shakashaka puzzle solver.

Rules:
- Place black triangles in white cells so that all white areas are rectangular.
- Triangles are right-angled and occupy half of a white square (diagonally).
- Triangles can only be placed in white cells.
- Numbers in black cells indicate how many triangles are adjacent (vertically/horizontally).
- White rectangles can be either axis-aligned or rotated at 45°.
"""

from .solver import BaseSolver


# Cell type constants for grid (from parser)
WHITE = -2
BLACK_NO_NUMBER = -1
# Black with clue n (0-4) stored as n

# Triangle placement: 0 = none, 1 = TL, 2 = TR, 3 = BL, 4 = BR (triangle in that corner)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_grid(table, height, width):
    """Convert parser table to grid: WHITE=-2, BLACK_NO_NUMBER=-1, black with clue 0-4 = 0..4.
    Parser: 0 is stored as 2; 'W'/'B' passed through.
    """
    grid = [[WHITE] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            v = table[r][c]
            if v == "W" or v == 2:
                grid[r][c] = WHITE
            elif v == "B" or v == 5 or (isinstance(v, int) and v > 4):
                grid[r][c] = BLACK_NO_NUMBER
            elif isinstance(v, int) and 0 <= v <= 4:
                grid[r][c] = v
            else:
                grid[r][c] = WHITE
    return grid


def _quadrant_grid(grid, board, height, width):
    """Build 2*height x 2*width grid of quadrants: True = white, False = black."""
    qh, qw = 2 * height, 2 * width
    q = [[False] * qw for _ in range(qh)]
    for r in range(height):
        for c in range(width):
            if grid[r][c] != WHITE:
                # Black cell: all 4 quadrants black
                continue
            val = board[r][c]
            if val == 0:
                # No triangle: all 4 white
                q[2 * r][2 * c] = True
                q[2 * r][2 * c + 1] = True
                q[2 * r + 1][2 * c] = True
                q[2 * r + 1][2 * c + 1] = True
            else:
                # Triangle in one corner: that quadrant black, others white
                q[2 * r][2 * c] = val != 1
                q[2 * r][2 * c + 1] = val != 2
                q[2 * r + 1][2 * c] = val != 3
                q[2 * r + 1][2 * c + 1] = val != 4
    return q


def _connected_white_components(q, qh, qw):
    """Return list of components, each a set of (i, j) quadrant coordinates."""
    visited = [[False] * qw for _ in range(qh)]
    components = []

    for i in range(qh):
        for j in range(qw):
            if not q[i][j] or visited[i][j]:
                continue
            comp = set()
            stack = [(i, j)]
            visited[i][j] = True
            comp.add((i, j))
            while stack:
                ni, nj = stack.pop()
                for di, dj in _D4:
                    ai, aj = ni + di, nj + dj
                    if 0 <= ai < qh and 0 <= aj < qw and q[ai][aj] and not visited[ai][aj]:
                        visited[ai][aj] = True
                        comp.add((ai, aj))
                        stack.append((ai, aj))
            components.append(comp)
    return components


def _is_axis_aligned_rectangle(comp):
    """Check if component (set of (i,j)) is an axis-aligned rectangle (no holes)."""
    if not comp:
        return True
    is_ = [p[0] for p in comp]
    js = [p[1] for p in comp]
    i_min, i_max = min(is_), max(is_)
    j_min, j_max = min(js), max(js)
    expected = (i_max - i_min + 1) * (j_max - j_min + 1)
    return len(comp) == expected


def _is_rotated_rectangle(comp, qh, qw):
    """Check if component is a 45° rotated rectangle (diamond) in (i+j, i-j) space."""
    if not comp:
        return True
    # Map (i, j) -> (s, t) with s = i+j, t = i-j. Bounding box in (s,t) space.
    s_vals = [p[0] + p[1] for p in comp]
    t_vals = [p[0] - p[1] for p in comp]
    s_min, s_max = min(s_vals), max(s_vals)
    t_min, t_max = min(t_vals), max(t_vals)
    # Component must equal the set of all (i,j) in grid with (i+j,i-j) in [s_min,s_max] x [t_min,t_max].
    # Lattice (i,j) with s=i+j, t=i-j satisfy i=(s+t)/2, j=(s-t)/2 so s and t must have same parity.
    expected = set()
    for s in range(s_min, s_max + 1):
        for t in range(t_min, t_max + 1):
            if (s - t) % 2 != 0:
                continue
            i = (s + t) // 2
            j = (s - t) // 2
            if 0 <= i < qh and 0 <= j < qw:
                expected.add((i, j))
    return comp == expected


def _white_areas_are_rectangles(grid, board, height, width):
    """Check that every connected white area is axis-aligned or 45° rotated rectangle."""
    q = _quadrant_grid(grid, board, height, width)
    qh, qw = 2 * height, 2 * width
    components = _connected_white_components(q, qh, qw)
    for comp in components:
        if _is_axis_aligned_rectangle(comp):
            continue
        if _is_rotated_rectangle(comp, qh, qw):
            continue
        return False
    return True


class ShakashakaSolver(BaseSolver):
    """Solver for Shakashaka puzzles.

    Input: grid from TableTaskParser. 2/W=white, 5/B=black no number, 0-4=black with clue.
    Output: 2D grid: 0=no triangle, 1=TL, 2=TR, 3=BL, 4=BR (only white cells are filled).
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.grid = _normalize_grid(info["table"], self.height, self.width)
        # board[r][c]: 0 = no triangle, 1 = TL, 2 = TR, 3 = BL, 4 = BR (only on white cells)
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.white_cells = [
            (r, c) for r in range(self.height) for c in range(self.width)
            if self.grid[r][c] == WHITE
        ]

    def _is_black(self, r, c):
        return self.grid[r][c] >= BLACK_NO_NUMBER and self.grid[r][c] != WHITE

    def _count_adjacent_triangles(self, r, c):
        """Count white cells orthogonally adjacent to (r,c) that have a triangle (any orientation)."""
        count = 0
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                if self.board[nr][nc] != 0:
                    count += 1
        return count

    def _black_constraints_ok(self, r, c):
        """Black cell (r,c): adjacent triangle count must match clue (if any)."""
        val = self.grid[r][c]
        if val == BLACK_NO_NUMBER:
            return True
        count = self._count_adjacent_triangles(r, c)
        return count <= val

    def _black_constraints_ok_around(self, r, c):
        """After changing (r,c), check all black neighbors still satisfiable."""
        cells_to_check = {(r, c)}
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                cells_to_check.add((nr, nc))
        for (rr, cc) in cells_to_check:
            if self._is_black(rr, cc) and not self._black_constraints_ok(rr, cc):
                return False
        return True

    def _can_black_still_be_satisfied(self, r, c, white_cells_from_idx):
        """True if black cell (r,c) can still get enough adjacent triangles.
        white_cells_from_idx = set of (r,c) that are still to be assigned (indices >= idx).
        """
        val = self.grid[r][c]
        if val == BLACK_NO_NUMBER:
            return True
        current = self._count_adjacent_triangles(r, c)
        if current > val:
            return False
        unassigned_adj = sum(
            1 for dr, dc in _D4
            for nr, nc in [(r + dr, c + dc)]
            if 0 <= nr < self.height and 0 <= nc < self.width
            and (nr, nc) in white_cells_from_idx
        )
        return current + unassigned_adj >= val

    def _all_black_can_be_satisfied(self, next_white_idx):
        """Check every numbered black cell can still reach its count (conservative)."""
        white_from = set(self.white_cells[next_white_idx:])
        for r in range(self.height):
            for c in range(self.width):
                if self._is_black(r, c) and not self._can_black_still_be_satisfied(r, c, white_from):
                    return False
        return True

    def solve(self):
        """Solve the Shakashaka puzzle. Returns 2D grid: 0=no triangle, 1-4=triangle corner."""
        n = len(self.white_cells)
        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress(idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                filled = sum(
                    1 for (r, c) in self.white_cells if self.board[r][c] != 0
                )
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=idx,
                    total_cells=n,
                )

            if idx >= n:
                # All black constraints already checked when placing; verify rectangle constraint
                return _white_areas_are_rectangles(self.grid, self.board, self.height, self.width)

            r, c = self.white_cells[idx]

            for choice in range(5):  # 0 = no triangle, 1..4 = TL, TR, BL, BR
                self.board[r][c] = choice
                if not self._black_constraints_ok_around(r, c):
                    continue
                if not self._all_black_can_be_satisfied(idx + 1):
                    continue
                if solve_with_progress(idx + 1):
                    return True
                backtrack_count[0] += 1

            self.board[r][c] = 0
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
