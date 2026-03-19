"""Dominosa puzzle solver.

Rules:
- Partition the number grid into dominoes (pairs of orthogonally adjacent cells).
- Domino values are unordered pairs (a, b).
- For max value N in the grid, each pair with 0 <= a <= b <= N must appear exactly once.
"""

from collections import Counter

from .solver import BaseSolver


_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _domino_type(a, b):
    """Canonical unordered pair key."""
    return (min(a, b), max(a, b))


def _expected_pairs(max_value):
    """Return required multiplicity for each pair in a full domino set 0..max_value."""
    counts = Counter()
    for a in range(max_value + 1):
        for b in range(a, max_value + 1):
            counts[(a, b)] = 1
    return counts


class DominosaSolver(BaseSolver):
    """Backtracking Dominosa solver.

    Output format:
    - [((r1, c1), (r2, c2)), ...]
      Each tuple describes one domino placement. This matches TableBetweenSubmitter.
    """

    def __init__(
        self,
        info,
        show_progress=True,
        partial_solution_callback=None,
        progress_interval=10.0,
        partial_interval=100.0,
    ):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.table = info["table"]
        self.max_value = max(max(row) for row in self.table)
        self.required = _expected_pairs(self.max_value)

        # -1 = not assigned to a domino yet.
        self.assignment = [[-1 for _ in range(self.width)] for _ in range(self.height)]
        self.placements = []
        self.edges_by_pair = self._build_edges_by_pair()
        self._pair_order_cache = []
        self._last_cache_filled_bucket = -1
        self._cache_refresh_cells = 100

    def _build_edges_by_pair(self):
        """Precompute all adjacent cell-edges grouped by domino pair type."""
        edges_by_pair = {pair: [] for pair in self.required}
        for r in range(self.height):
            for c in range(self.width):
                for dr, dc in ((0, 1), (1, 0)):
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < self.height and 0 <= nc < self.width):
                        continue
                    pair = _domino_type(self.table[r][c], self.table[nr][nc])
                    edges_by_pair[pair].append(((r, c), (nr, nc)))
        return edges_by_pair

    def _choose_next_pair(self):
        """Pick remaining pair with the fewest currently available placements."""
        best_pair = None
        best_options = None

        for pair, needed in self.remaining.items():
            if needed <= 0:
                continue
            options = []
            for (a, b) in self.edges_by_pair.get(pair, []):
                ar, ac = a
                br, bc = b
                if self.assignment[ar][ac] != -1 or self.assignment[br][bc] != -1:
                    continue
                options.append((a, b))

            if best_options is None or len(options) < len(best_options):
                best_pair = pair
                best_options = options
                if len(best_options) <= 1:
                    return best_pair, best_options

        return best_pair, best_options

    def _rebuild_pair_order_cache(self):
        """Rebuild pair order cache sorted by current number of available placements."""
        scored = []
        for pair, needed in self.remaining.items():
            if needed <= 0:
                continue
            count = 0
            for (a, b) in self.edges_by_pair.get(pair, []):
                ar, ac = a
                br, bc = b
                if self.assignment[ar][ac] == -1 and self.assignment[br][bc] == -1:
                    count += 1
            scored.append((count, pair))
        scored.sort(key=lambda x: x[0])
        self._pair_order_cache = [pair for _, pair in scored]

    def _choose_next_pair_from_cache(self):
        """Choose pair using cached order, falling back to full recompute if needed."""
        for pair in self._pair_order_cache:
            if self.remaining.get(pair, 0) <= 0:
                continue
            options = []
            for (a, b) in self.edges_by_pair.get(pair, []):
                ar, ac = a
                br, bc = b
                if self.assignment[ar][ac] != -1 or self.assignment[br][bc] != -1:
                    continue
                options.append((a, b))
            return pair, options
        return self._choose_next_pair()

    def _snapshot_placements(self):
        """Immutable snapshot for partial-submit callbacks."""
        return [((a[0], a[1]), (b[0], b[1])) for (a, b) in self.placements]

    def _find_forced_cell_move(self):
        """Return a forced move if any unassigned cell has exactly one valid neighbor.

        Returns:
            ("contradiction", None): unassigned cell has no valid neighbor
            ("forced", (a, b, pair)): one forced edge
            ("none", None): no forced cell move
        """
        for r in range(self.height):
            for c in range(self.width):
                if self.assignment[r][c] != -1:
                    continue
                options = []
                for dr, dc in _D4:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < self.height and 0 <= nc < self.width):
                        continue
                    if self.assignment[nr][nc] != -1:
                        continue
                    pair = _domino_type(self.table[r][c], self.table[nr][nc])
                    if self.remaining[pair] > 0:
                        options.append(((r, c), (nr, nc), pair))
                if len(options) == 0:
                    return "contradiction", None
                if len(options) == 1:
                    return "forced", options[0]
        return "none", None

    def _backtrack(self, call_count, backtrack_count):
        call_count[0] += 1
        filled_cells = len(self.placements) * 2
        filled_bucket = filled_cells // self._cache_refresh_cells
        if filled_bucket != self._last_cache_filled_bucket:
            self._rebuild_pair_order_cache()
            self._last_cache_filled_bucket = filled_bucket

        if self.progress_tracker and call_count[0] % 250 == 0:
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                cells_filled=filled_cells,
                total_cells=self.height * self.width,
                current_board=self._snapshot_placements(),
            )

        forced_state, forced_move = self._find_forced_cell_move()
        if forced_state == "contradiction":
            return False
        if forced_state == "forced":
            a, b, pair = forced_move
            ar, ac = a
            br, bc = b
            domino_id = len(self.placements)
            self.assignment[ar][ac] = domino_id
            self.assignment[br][bc] = domino_id
            self.remaining[pair] -= 1
            self.placements.append((a, b))

            if self._backtrack(call_count, backtrack_count):
                return True

            self.placements.pop()
            self.remaining[pair] += 1
            self.assignment[ar][ac] = -1
            self.assignment[br][bc] = -1
            backtrack_count[0] += 1
            return False

        pair, options = self._choose_next_pair_from_cache()
        if pair is None:
            return True
        if not options:
            return False

        domino_id = len(self.placements)
        for (a, b) in options:
            ar, ac = a
            br, bc = b
            self.assignment[ar][ac] = domino_id
            self.assignment[br][bc] = domino_id
            self.remaining[pair] -= 1
            self.placements.append((a, b))

            if self._backtrack(call_count, backtrack_count):
                return True

            self.placements.pop()
            self.remaining[pair] += 1
            self.assignment[ar][ac] = -1
            self.assignment[br][bc] = -1
            backtrack_count[0] += 1

        return False

    def solve(self):
        """Solve Dominosa and return pair-click moves."""
        total_cells = self.height * self.width
        if total_cells % 2 != 0:
            return None

        expected_dominoes = len(self.required)
        if total_cells != 2 * expected_dominoes:
            return None

        value_counts = Counter(v for row in self.table for v in row)
        required_count_per_value = self.max_value + 2
        for v in range(self.max_value + 1):
            if value_counts[v] != required_count_per_value:
                return None

        self.remaining = Counter(self.required)
        call_count = [0]
        backtrack_count = [0]
        self._rebuild_pair_order_cache()
        self._last_cache_filled_bucket = 0

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = self._backtrack(call_count, backtrack_count)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return list(self.placements)
