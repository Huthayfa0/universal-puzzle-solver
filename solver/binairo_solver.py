"""Binairo solver. Rules: equal black/white per row and column; max two same adjacent; all rows and columns unique."""

from .solver import BaseSolver

EMPTY = 0
BLACK = 1
WHITE = 2


def _normalize_cell(value):
    """Map parser output to EMPTY, BLACK, or WHITE."""
    if value in (0, -1, 2):
        return EMPTY
    if value in ("B", "b", 1):
        return BLACK
    if value in ("W", "w"):
        return WHITE
    return BLACK


class BinairoSolver(BaseSolver):
    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                        progress_interval=progress_interval, partial_interval=partial_interval)
        self.row_half = self.width // 2   # each row has width cells -> half each color
        self.col_half = self.height // 2  # each column has height cells -> half each color
        self.board = [[EMPTY for _ in range(self.width)] for _ in range(self.height)]
        raw = info.get("table", [])
        for i in range(self.height):
            for j in range(self.width):
                if i < len(raw) and j < len(raw[i]):
                    self.board[i][j] = _normalize_cell(raw[i][j])

    def _get_row(self, i):
        return self.board[i][:]

    def _get_col(self, j):
        return [self.board[i][j] for i in range(self.height)]

    def _no_three_adjacent(self, line):
        for k in range(len(line) - 2):
            if line[k] != EMPTY and line[k] == line[k + 1] == line[k + 2]:
                return False
        return True

    def _no_three_adjacent_anywhere(self):
        """No row and no column has three consecutive cells of the same color."""
        for i in range(self.height):
            if not self._no_three_adjacent(self._get_row(i)):
                return False
        for j in range(self.width):
            if not self._no_three_adjacent(self._get_col(j)):
                return False
        return True

    def _is_valid_line(self, line):
        """Line is valid if counts <= half and no three adjacent. Uses len(line)//2 for half (works for rows and cols)."""
        half = len(line) // 2
        w = sum(1 for c in line if c == WHITE)
        b = sum(1 for c in line if c == BLACK)
        if w > half or b > half:
            return False
        return self._no_three_adjacent(line)

    def _is_valid_placement(self, r, c, color):
        self.board[r][c] = color
        ok = self._is_valid_line(self._get_row(r)) and self._is_valid_line(self._get_col(c))
        self.board[r][c] = EMPTY
        return ok

    def _rows_unique(self):
        rows = [tuple(self._get_row(i)) for i in range(self.height)]
        filled = [r for r in rows if EMPTY not in r]
        return len(filled) == len(set(filled))

    def _cols_unique(self):
        cols = [tuple(self._get_col(j)) for j in range(self.width)]
        filled = [c for c in cols if EMPTY not in c]
        return len(filled) == len(set(filled))

    def _counts_valid(self):
        """Mid-solve: no row/column exceeds its half (width//2 per row, height//2 per col)."""
        for i in range(self.height):
            w = sum(1 for c in self.board[i] if c == WHITE)
            b = sum(1 for c in self.board[i] if c == BLACK)
            if w > self.row_half or b > self.row_half:
                return False
        for j in range(self.width):
            w = sum(1 for i in range(self.height) if self.board[i][j] == WHITE)
            b = sum(1 for i in range(self.height) if self.board[i][j] == BLACK)
            if w > self.col_half or b > self.col_half:
                return False
        return True

    def _all_counts_correct(self):
        """Every row and column has exactly half white and half black (row_half/col_half)."""
        for i in range(self.height):
            w = sum(1 for c in self.board[i] if c == WHITE)
            b = sum(1 for c in self.board[i] if c == BLACK)
            if w != self.row_half or b != self.row_half:
                return False
        for j in range(self.width):
            w = sum(1 for i in range(self.height) if self.board[i][j] == WHITE)
            b = sum(1 for i in range(self.height) if self.board[i][j] == BLACK)
            if w != self.col_half or b != self.col_half:
                return False
        return True

    def _propagate_line(self, line, target_half):
        """Fill forced cells: Rule 2 (no three adjacent) first, then Rule 1 (equal count) if it doesn't break Rule 2."""
        line = list(line)
        n = len(line)
        total_changes = 0
        other = lambda c: BLACK if c == WHITE else WHITE

        while True:
            round_changes = 0
            # Two same color in a row -> the cell next to them (before or after) must be the other color
            for k in range(n - 2):
                a, mid, c = line[k], line[k + 1], line[k + 2]
                if mid == EMPTY and a != EMPTY and a == c:
                    line[k + 1] = other(a)
                    round_changes += 1
                elif line[k + 2] == EMPTY and a != EMPTY and a == mid:
                    line[k + 2] = other(a)
                    round_changes += 1
                elif line[k] == EMPTY and mid != EMPTY and mid == c:
                    line[k] = other(c)
                    round_changes += 1
            # Explicit pass: for every pair of consecutive same color, force the adjacent cell(s)
            for i in range(n - 1):
                if line[i] != EMPTY and line[i] == line[i + 1]:
                    col = line[i]
                    if i + 2 < n and line[i + 2] == EMPTY:
                        line[i + 2] = other(col)
                        round_changes += 1
                    if i - 1 >= 0 and line[i - 1] == EMPTY:
                        line[i - 1] = other(col)
                        round_changes += 1
            total_changes += round_changes
            if round_changes == 0:
                break

        w, b = sum(1 for c in line if c == WHITE), sum(1 for c in line if c == BLACK)
        empties = [i for i in range(n) if line[i] == EMPTY]
        if len(empties) == 1:
            idx = empties[0]
            if w == target_half - 1 and b == target_half:
                line[idx] = WHITE
                if self._no_three_adjacent(line):
                    total_changes += 1
                else:
                    line[idx] = EMPTY
            elif b == target_half - 1 and w == target_half:
                line[idx] = BLACK
                if self._no_three_adjacent(line):
                    total_changes += 1
                else:
                    line[idx] = EMPTY
        elif empties:
            # One color already at half -> fill all remaining empties with the other color (if no three adjacent)
            if w == target_half:
                for idx in empties:
                    line[idx] = BLACK
                if self._no_three_adjacent(line):
                    total_changes += len(empties)
                else:
                    for idx in empties:
                        line[idx] = EMPTY
            elif b == target_half:
                for idx in empties:
                    line[idx] = WHITE
                if self._no_three_adjacent(line):
                    total_changes += len(empties)
                else:
                    for idx in empties:
                        line[idx] = EMPTY

        return line, total_changes

    def _propagate(self):
        """Fill cells only when row and column agree (or only one forces), to avoid conflicts."""
        row_forced = [self._propagate_line(self._get_row(i), self.row_half)[0] for i in range(self.height)]
        col_forced = [self._propagate_line(self._get_col(j), self.col_half)[0] for j in range(self.width)]
        changed = False
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] != EMPTY:
                    continue
                r, c = row_forced[i][j], col_forced[j][i]
                if r != EMPTY and c != EMPTY and r != c:
                    continue
                if r != EMPTY or c != EMPTY:
                    self.board[i][j] = r if r != EMPTY else c
                    changed = True
        return changed

    def _sort_cell_order_from(self, cell_idx):
        """Re-sort cell_order[cell_idx:] by current constraint (fewer empties in row+col first)."""
        empty_in_row = [sum(1 for j in range(self.width) if self.board[i][j] == EMPTY) for i in range(self.height)]
        empty_in_col = [sum(1 for i in range(self.height) if self.board[i][j] == EMPTY) for j in range(self.width)]
        key = lambda ij: (min(empty_in_row[ij[0]] , empty_in_col[ij[1]]), max(empty_in_row[ij[0]] , empty_in_col[ij[1]]), ij[0], ij[1])
        self.cell_order[cell_idx:] = sorted(self.cell_order[cell_idx:], key=key)

    _PROPAGATE_EVERY = 6

    def _is_solution_complete(self):
        """Return True if the current board is a valid complete solution (override in subclasses)."""
        return (
            self._no_three_adjacent_anywhere()
            and self._all_counts_correct()
            and self._rows_unique()
            and self._cols_unique()
        )

    def _solve_at(self, cell_idx, backtrack_count=None):
        if backtrack_count is None:
            backtrack_count = [0]
        total = self.height * self.width
        if cell_idx >= total:
            return self._is_solution_complete()

        if cell_idx > 0 and cell_idx % self._PROPAGATE_EVERY == 0:
            while self._propagate():
                pass
            self._sort_cell_order_from(cell_idx)
            if not self._counts_valid():
                return False  # parent will restore board_save and backtrack

        i, j = self.cell_order[cell_idx]
        filled = sum(1 for r in range(self.height) for c in range(self.width) if self.board[r][c] != EMPTY)
        self._update_progress(cell_idx=cell_idx, total_cells=total, cells_filled=filled, current_cell=(i, j), backtrack_count=backtrack_count[0])

        if self.board[i][j] != EMPTY:
            return self._solve_at(cell_idx + 1, backtrack_count)

        board_save = [row[:] for row in self.board]
        for color in (WHITE, BLACK):
            if not self._is_valid_placement(i, j, color):
                continue
            self.board[i][j] = color
            if not self._counts_valid():
                continue
            if self._solve_at(cell_idx + 1, backtrack_count):
                return True
            for r in range(self.height):
                for c in range(self.width):
                    self.board[r][c] = board_save[r][c]
            backtrack_count[0] += 1
        return False

    def solve(self):
        self.cell_order = [(i, j) for i in range(self.height) for j in range(self.width)]
        self._sort_cell_order_from(0)
        total = self.height * self.width
        filled = sum(1 for i in range(self.height) for j in range(self.width) if self.board[i][j] != EMPTY)
        self._update_progress(cell_idx=0, total_cells=total, cells_filled=filled, current_cell=self.cell_order[0], backtrack_count=0)
        while self._propagate():
            pass
        self._sort_cell_order_from(0)
        if not self._counts_valid():
            raise ValueError("Binairo puzzle has no solution (invalid counts after propagation)")
        if not self._solve_at(0):
            raise ValueError("Binairo puzzle has no solution")
        return self.board
