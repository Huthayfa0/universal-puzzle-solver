"""Kakuro puzzle solver.

Rules:
1. Each cell can contain numbers from 1 through 9.
2. The clues in the black cells give the sum of the numbers in the white cells
   to the right (across) or down from that clue.
3. The numbers in each block (run) of white cells must be unique.
"""

from .solver import BaseSolver


def _build_runs(height, width, is_white, down_clues, across_clues):
    """Build horizontal and vertical runs from grid and clue arrays.

    is_white[r][c] True iff cell (r,c) is white.
    down_clues[r][c] = sum for vertical run starting below (r,c), or 0.
    across_clues[r][c] = sum for horizontal run starting right of (r,c), or 0.

    Returns:
        horizontal_runs: list of (target_sum, [(r,c), ...])
        vertical_runs: list of (target_sum, [(r,c), ...])
    """
    horizontal_runs = []
    vertical_runs = []

    # Horizontal runs: for each row, find contiguous white segments; clue is in the black cell to the left
    for r in range(height):
        c = 0
        while c < width:
            if not is_white[r][c]:
                c += 1
                continue
            # Start of a white run; the clue is in (r, c-1) if c > 0
            run_cells = []
            start_c = c
            while c < width and is_white[r][c]:
                run_cells.append((r, c))
                c += 1
            # Clue for this run: across_clues[r][start_c - 1] (cell to the left of run)
            clue_c = start_c - 1
            if clue_c >= 0 and across_clues[r][clue_c] > 0:
                horizontal_runs.append((across_clues[r][clue_c], run_cells))
            c += 1

    # Vertical runs: for each column, find contiguous white segments; clue is in the black cell above
    for c in range(width):
        r = 0
        while r < height:
            if not is_white[r][c]:
                r += 1
                continue
            run_cells = []
            start_r = r
            while r < height and is_white[r][c]:
                run_cells.append((r, c))
                r += 1
            clue_r = start_r - 1
            if clue_r >= 0 and down_clues[clue_r][c] > 0:
                vertical_runs.append((down_clues[clue_r][c], run_cells))
            r += 1

    return horizontal_runs, vertical_runs


def _runs_for_cell(horizontal_runs, vertical_runs):
    """Return (h_run_index, v_run_index) for each white cell, by building a map from (r,c)."""
    cell_to_h = {}  # (r,c) -> index in horizontal_runs
    cell_to_v = {}
    for idx, (_, cells) in enumerate(horizontal_runs):
        for rc in cells:
            cell_to_h[rc] = idx
    for idx, (_, cells) in enumerate(vertical_runs):
        for rc in cells:
            cell_to_v[rc] = idx
    return cell_to_h, cell_to_v


class KakuroSolver(BaseSolver):
    """Solver for Kakuro puzzles.

    Expects in info:
        height, width: grid size
        table: 2D grid, 0 or 2 = white, 1 = black (parser uses 2 for 0)
        down_clues: 2D, clue value for vertical run below this cell, 0 if not a clue cell
        across_clues: 2D, clue value for horizontal run right of this cell, 0 if not a clue cell
    Solution: 2D grid with 0 for black cells, 1-9 for white cells.
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        # Normalize: white = 0, black = 1 in table (parser may use 2 for 0)
        raw_table = info["table"]
        self.is_white = []
        for row in raw_table:
            self.is_white.append([(c == 0 or c == 2) for c in row])  # 0 or 2 = white

        down_clues = info["down_clues"]
        across_clues = info["across_clues"]

        self.horizontal_runs, self.vertical_runs = _build_runs(
            self.height, self.width, self.is_white, down_clues, across_clues
        )
        self.cell_to_h, self.cell_to_v = _runs_for_cell(self.horizontal_runs, self.vertical_runs)

        # Board: 0 = black (unused for submission of digits), 1-9 = digit in white cell
        # We only fill white cells; black stay 0 for output
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for r in range(self.height):
            for c in range(self.width):
                if self.is_white[r][c]:
                    self.board[r][c] = 0  # empty white

        # For each run, track current sum and used digits
        self.h_sum = [0] * len(self.horizontal_runs)
        self.h_used = [set() for _ in range(len(self.horizontal_runs))]
        self.v_sum = [0] * len(self.vertical_runs)
        self.v_used = [set() for _ in range(len(self.vertical_runs))]

        # Ordered list of white cells for backtracking (e.g. row-major)
        self.white_cells = [
            (r, c) for r in range(self.height) for c in range(self.width)
            if self.is_white[r][c]
        ]

    def _run_allows(self, num, r, c):
        """Check if placing num at (r,c) is valid for both its horizontal and vertical runs."""
        h_idx = self.cell_to_h.get((r, c))
        v_idx = self.cell_to_v.get((r, c))
        if h_idx is None or v_idx is None:
            return False

        target_h, cells_h = self.horizontal_runs[h_idx]
        target_v, cells_v = self.vertical_runs[v_idx]

        if num in self.h_used[h_idx] or num in self.v_used[v_idx]:
            return False

        new_h_sum = self.h_sum[h_idx] + num
        new_v_sum = self.v_sum[v_idx] + num
        if new_h_sum > target_h or new_v_sum > target_v:
            return False

        # Count unfilled in each run
        unfilled_h = sum(1 for (rr, cc) in cells_h if self.board[rr][cc] == 0) - 1
        unfilled_v = sum(1 for (rr, cc) in cells_v if self.board[rr][cc] == 0) - 1

        # Min/max we can still add in the rest of the run (unique 1-9)
        def min_max_remaining(used, n_empty):
            if n_empty <= 0:
                return (0, 0)
            available = [x for x in range(1, 10) if x not in used]
            available.sort()
            min_r = sum(available[:n_empty])
            max_r = sum(available[-n_empty:])
            return (min_r, max_r)

        min_h, max_h = min_max_remaining(self.h_used[h_idx] | {num}, unfilled_h)
        min_v, max_v = min_max_remaining(self.v_used[v_idx] | {num}, unfilled_v)

        if new_h_sum + min_h > target_h or new_h_sum + max_h < target_h:
            return False
        if new_v_sum + min_v > target_v or new_v_sum + max_v < target_v:
            return False

        return True

    def solve(self):
        """Solve the Kakuro puzzle. Returns 2D grid: 0 for black, 1-9 for white cells."""
        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()

        call_count = [0]

        def solve_with_progress(cell_idx):
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                filled = sum(1 for r, c in self.white_cells if self.board[r][c] != 0)
                self._update_progress(
                    call_count=call_count[0],
                    cells_filled=filled,
                    total_cells=len(self.white_cells),
                )

            if cell_idx >= len(self.white_cells):
                return True

            r, c = self.white_cells[cell_idx]
            h_idx = self.cell_to_h[(r, c)]
            v_idx = self.cell_to_v[(r, c)]

            for num in range(1, 10):
                if not self._run_allows(num, r, c):
                    continue

                self.board[r][c] = num
                self.h_sum[h_idx] += num
                self.h_used[h_idx].add(num)
                self.v_sum[v_idx] += num
                self.v_used[v_idx].add(num)

                if solve_with_progress(cell_idx + 1):
                    return True

                self.board[r][c] = 0
                self.h_sum[h_idx] -= num
                self.h_used[h_idx].discard(num)
                self.v_sum[v_idx] -= num
                self.v_used[v_idx].discard(num)

            return False

        try:
            ok = solve_with_progress(0)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [[self.board[r][c] for c in range(self.width)] for r in range(self.height)]
