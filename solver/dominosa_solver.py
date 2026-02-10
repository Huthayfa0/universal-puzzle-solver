"""Dominosa puzzle solver.

Rules:
- The grid shows numbers. Partition the grid into dominoes (each domino = 2 adjacent cells).
- Each domino is an unordered pair of numbers (a, b). Every such pair from 0..N appears exactly once.
- Find the location of all dominoes (which adjacent cells form which pair).
"""

from collections import Counter

from .solver import BaseSolver


# 4 directions: right, down, left, up (for pairing)
_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_table(table):
    """Convert parser table to 0-based digits. Parser stores 0 as 2."""
    return [[0 if c == 2 else c for c in row] for row in table]


def _domino_type(a, b):
    """Canonical unordered pair for domino (a, b)."""
    return (min(a, b), max(a, b))


def _expected_domino_counts(n):
    """Return Counter of how many of each domino type we need for digits 0..n.
    Each unordered pair (i,j) appears exactly once."""
    counts = Counter()
    for i in range(n + 1):
        for j in range(i, n + 1):
            counts[(i, j)] = 1
    return counts


class DominosaSolver(BaseSolver):
    """Solver for Dominosa puzzles.

    Input: grid of numbers (from TableTaskParser). 0 is stored as 2 by parser.
    Output: 2D grid where each cell has a domino ID (1-based). Same ID for both cells of a domino.
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
        self.n = max(max(row) for row in self.table)
        self.expected = _expected_domino_counts(self.n)
        self.num_dominoes = (self.n + 1) * (self.n + 2) // 2
        # assignment[r][c] = domino_id (0-based) or -1 if unassigned
        self.assignment = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        self.next_domino_id = 0

    def _remaining(self):
        """Current count of each domino type still to place (copy we can mutate)."""
        return Counter(self.expected)

    def _solve(self, remaining, cell_list_idx):
        """Backtrack: assign dominoes. cell_list_idx indexes into a fixed ordering of cells."""
        if cell_list_idx >= len(self._cell_list):
            return True

        r, c = self._cell_list[cell_list_idx]
        if self.assignment[r][c] != -1:
            return self._solve(remaining, cell_list_idx + 1)

        a = self.table[r][c]
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < self.height and 0 <= nc < self.width):
                continue
            if self.assignment[nr][nc] != -1:
                continue
            b = self.table[nr][nc]
            pair = _domino_type(a, b)
            if remaining[pair] <= 0:
                continue

            dom_id = self.next_domino_id
            self.next_domino_id += 1
            self.assignment[r][c] = dom_id
            self.assignment[nr][nc] = dom_id
            remaining[pair] -= 1

            if self._solve(remaining, cell_list_idx + 1):
                return True

            self.assignment[r][c] = -1
            self.assignment[nr][nc] = -1
            self.next_domino_id -= 1
            remaining[pair] += 1

        return False

    def solve(self):
        """Solve the Dominosa puzzle. Returns 2D grid of 1-based domino IDs (same ID for both cells of a domino)."""
        total_cells = self.height * self.width
        required_cells = (self.n + 1) * (self.n + 2)
        if total_cells != required_cells:
            return None

        self._cell_list = [(r, c) for r in range(self.height) for c in range(self.width)]

        remaining = self._remaining()
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()

        try:
            ok = self._solve(remaining, 0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None

        # Convert to 1-based IDs for submission (0 = skip in TableSubmitter; we want every cell filled)
        return [[self.assignment[r][c] + 1 for c in range(self.width)] for r in range(self.height)]
