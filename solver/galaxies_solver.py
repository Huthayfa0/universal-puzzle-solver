"""Galaxies puzzle solver.

Rules:
- Each region has exactly 1 white circle in it.
- The circle is the center of its rotational symmetry: rotating the region
  around the circle at 180° gives the same shape, position and orientation.
"""

from .solver import BaseSolver

_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _region_to_walls(region, height, width):
    """Convert region[r][c] (center index per cell) to horizontal/vertical walls."""
    h_walls = [[0] * (width - 1) for _ in range(height)]
    v_walls = [[0] * width for _ in range(height - 1)]
    for r in range(height):
        for c in range(width - 1):
            if region[r][c] != region[r][c + 1]:
                h_walls[r][c] = 1
    for r in range(height - 1):
        for c in range(width):
            if region[r][c] != region[r + 1][c]:
                v_walls[r][c] = 1
    return {"horizontal_walls": h_walls, "vertical_walls": v_walls}


def _is_connected(region, height, width, center_idx, centers):
    """Check that all cells with region[r][c]==center_idx are 4-connected."""
    cr, cc = centers[center_idx]
    seen = set()
    stack = [(cr, cc)]
    seen.add((cr, cc))
    count = 0
    for r in range(height):
        for c in range(width):
            if region[r][c] == center_idx:
                count += 1
    while stack:
        r, c = stack.pop()
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in seen:
                if region[nr][nc] == center_idx:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
    return len(seen) == count


class GalaxiesSolver(BaseSolver):
    """Solver for Galaxies (Spiral Galaxies) puzzles.

    Input: grid from ShingokiTaskParser (or similar): table with 0=empty, 1=circle.
    Output: dict with "horizontal_walls" (height x (width-1)) and
    "vertical_walls" ((height-1) x width), 1 = wall between regions, 0 = no wall.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.table = info["table"]
        # Normalize: 1 = circle (center), else = empty (parser may use 0 or 2 for empty)
        self.centers = []
        for r in range(self.height):
            for c in range(self.width):
                if self.table[r][c] == 1:
                    self.centers.append((r, c))
        self.num_centers = len(self.centers)
        # region[r][c] = center index (0..num_centers-1) or -1
        self.region = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        for idx, (r, c) in enumerate(self.centers):
            self.region[r][c] = idx

    def _twin(self, r, c, center_idx):
        """Return the 180° twin of (r,c) around centers[center_idx]."""
        cr, cc = self.centers[center_idx]
        return (2 * cr - r, 2 * cc - c)

    def _unassigned_cell(self):
        """Return the first unassigned cell in row-major order, or None."""
        for r in range(self.height):
            for c in range(self.width):
                if self.region[r][c] == -1:
                    return (r, c)
        return None

    def solve(self):
        """Solve the Galaxies puzzle. Returns dict with horizontal_walls and vertical_walls."""
        total_cells = self.height * self.width
        if self.num_centers == 0:
            return None
        if total_cells % self.num_centers != 0:
            return None

        call_count = [0]
        backtrack_count = [0]

        def solve_with_progress():
            call_count[0] += 1
            if self.progress_tracker and call_count[0] % 500 == 0:
                assigned = sum(1 for r in range(self.height) for c in range(self.width) if self.region[r][c] >= 0)
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=assigned,
                    total_cells=total_cells,
                )

            cell = self._unassigned_cell()
            if cell is None:
                for idx in range(self.num_centers):
                    if not _is_connected(self.region, self.height, self.width, idx, self.centers):
                        return False
                return True

            r, c = cell
            for idx in range(self.num_centers):
                cr, cc = self.centers[idx]
                tr, tc = self._twin(r, c, idx)
                if not (0 <= tr < self.height and 0 <= tc < self.width):
                    continue
                twin_val = self.region[tr][tc]
                if twin_val != -1 and twin_val != idx:
                    continue
                old_self = self.region[r][c]
                old_twin = self.region[tr][tc]
                self.region[r][c] = idx
                if (tr, tc) != (r, c):
                    self.region[tr][tc] = idx

                if solve_with_progress():
                    return True

                self.region[r][c] = old_self
                self.region[tr][tc] = old_twin
                backtrack_count[0] += 1

            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = solve_with_progress()
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return _region_to_walls(self.region, self.height, self.width)
