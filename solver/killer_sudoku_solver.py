from .sudoku_solver import SudokuSolver
class KillerSudokuSolver(SudokuSolver):
    def __init__(self, info):
        super().__init__(info)
        self.trim_is_overkill = False
        self.sum_boxes = self.info["boxes" if self.subtable_type == "regular" else "boxes_2"] #dict of the indecies of each box
        self.sum_boxes_table = self.info["boxes_table" if self.subtable_type == "regular" else "boxes_table_2"] #the box in each cell
        self.sums = [value for row in self.info["table_2"] for value in row if value != 0]
        self.killer_x =info.get("killer_x", False) # True if there is an x codition other wise False

  
    # --------------------------------------------------
    def _cage_info(self, row, col):
        box = self.sum_boxes_table[row][col]
        cells = self.sum_boxes[box]
        target = self.sums[box]

        values = [
            self.board[r][c]
            for r, c in cells
            if self.board[r][c] != 0
        ]

        empty = sum(
            1 for r, c in cells
            if self.board[r][c] == 0
        )

        return values, empty, target

    def _cage_allows(self, num, row, col):
        values, empty, target = self._cage_info(row, col)

        if num in values:
            return False

        s = sum(values) + num
        if s > target:
            return False

        if empty == 1:
            return s == target

        remaining = empty - 1
        unused = set(range(1, self.height + 1)) - set(values) - {num}

        min_possible = sum(sorted(unused)[:remaining])
        max_possible = sum(sorted(unused, reverse=True)[:remaining])

        return (s + min_possible <= target) and (s + max_possible >= target)

    def _x_allows(self, num, row, col):
        if not self.killer_x:
            return True

        n = self.height

        # main diagonal
        if row == col:
            for i in range(n):
                if self.board[i][i] == num:
                    return False

        # anti-diagonal
        if row + col == n - 1:
            for i in range(n):
                if self.board[i][n - 1 - i] == num:
                    return False

        return True

    # --------------------------------------------------
    # Validity
    # --------------------------------------------------
    def is_valid(self, num, row, col):
        return (
            super().is_valid(num, row, col)
            and self._x_allows(num, row, col)
            and self._cage_allows(num, row, col)
        )

    # --------------------------------------------------
    # Possible values
    # --------------------------------------------------
    def possible_values(self, row, col):
        values = set(super().possible_values(row, col))

        allowed = {
            n for n in values
            if self._x_allows(n, row, col)
            and self._cage_allows(n, row, col)
        }

        self.possible_values_cache[(row, col)] = allowed
        return list(allowed)

    # --------------------------------------------------
    # Trimming
    # --------------------------------------------------
    def possible_values_trim(self):
        updated = super().possible_values_trim()

        for (i, j), vals in list(self.possible_values_cache.items()):
            if self.board[i][j] != 0:
                continue

            to_remove = {
                n for n in vals
                if not self._x_allows(n, i, j)
                or not self._cage_allows(n, i, j)
            }

            if to_remove:
                self.possible_values_cache[(i, j)] -= to_remove
                updated += len(to_remove)

        return updated
