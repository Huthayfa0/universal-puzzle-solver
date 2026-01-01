from .solver import BaseSolver
from itertools import combinations

class SudokuSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.board = info["table"] if "table" in info else [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.possible_values_cache = {}
        self.cells_to_fill = []
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 0:
                    self.cells_to_fill.append((i, j))
        self.subtable_type = info["subtable_type"]
        if self.subtable_type == "regular":
            self.subtable_height = self.info["subtable_height"]
            self.subtable_width = self.info["subtable_width"]
        elif self.subtable_type == "irregular":
            self.boxes = self.info["boxes"] #dict of the indecies of each box
            self.boxes_table = self.info["boxes_table"] #the box in each cell
        self.Kmax = max(self.height//2,2)
        self.trim_is_overkill = True 
        

    def is_valid(self, num, row, col):
        for x in range(self.width):
            if self.board[row][x] == num:
                return False
        for x in range(self.height):
            if self.board[x][col] == num:
                return False
        if self.subtable_type == "regular":
            start_row, start_col = self.subtable_height * (row // self.subtable_height), self.subtable_width * (col // self.subtable_width)
            for i in range(self.subtable_height):
                for j in range(self.subtable_width):
                    if self.board[start_row + i][start_col + j] == num:
                        return False
        elif self.subtable_type == "irregular":
            box_id = self.boxes_table[row][col]
            for r, c in self.boxes[box_id]:
                if self.board[r][c] == num:
                    return False
        return True
    
    def possible_values(self,row, col):
        values = set(range(1, self.width + 1))
        for x in range(self.width):
            if self.board[row][x] in values:
                values.remove(self.board[row][x])
        for x in range(self.height):
            if self.board[x][col] in values:
                values.remove(self.board[x][col])
        if self.subtable_type == "regular":
            start_row, start_col = self.subtable_height * (row // self.subtable_height), self.subtable_width * (col // self.subtable_width)
            for r in range(self.subtable_height):
                for c in range(self.subtable_width):
                    if self.board[start_row + r][start_col + c] in values:
                        values.remove(self.board[start_row + r][start_col + c])
        elif self.subtable_type == "irregular":
            box_id = self.boxes_table[row][col]
            for r, c in self.boxes[box_id]:
                if self.board[r][c] in values:
                    values.remove(self.board[r][c])

        self.possible_values_cache[(row, col)] = values
        return list(values)
    
    def possible_values_extended(self,row, col):
        values = self.possible_values_cache[(row, col)]
        return list(values)
    
    def regular_table_trim(self):
        updated = 0
        for r0 in range(0, self.height, self.subtable_height):
            for c0 in range(0,self.width, self.subtable_width):
                # collect candidates in this box
                num_positions = {n: [] for n in range(1, self.width + 1)}

                for r in range(r0, r0 + self.subtable_height):
                    for c in range(c0, c0 + self.subtable_width):
                        if (r, c) in self.possible_values_cache:
                            for n in self.possible_values_cache[(r, c)]:
                                num_positions[n].append((r, c))

                # analyze each number
                for n, cells in num_positions.items():
                    if len(cells) == 0:
                        continue
                    if len(cells) == 1:
                        r, c = cells[0]
                        if (r, c) in self.possible_values_cache and n in self.possible_values_cache[(r, c)]:
                            updated += len(self.possible_values_cache[(r, c)])-1
                            self.possible_values_cache[(r, c)] = {n}
                        continue

                    rows = {r for r, _ in cells}
                    cols = {c for _, c in cells}

                    # Row restriction
                    if len(rows) == 1:
                        row = rows.pop()
                        for c in range(self.width):
                            if not (c0 <= c < c0 + self.subtable_width):
                                if (row, c) in self.possible_values_cache and n in self.possible_values_cache[(row, c)]:
                                    self.possible_values_cache[(row, c)].remove(n)
                                    updated +=1

                    # Column restriction
                    if len(cols) == 1:
                        col = cols.pop()
                        for r in range(self.height):
                            if not (r0 <= r < r0 + self.subtable_height):
                                if (r, col) in self.possible_values_cache and n in self.possible_values_cache[(r, col)]:
                                    self.possible_values_cache[(r, col)].remove(n)
                                    updated +=1
        return updated
    def irregular_table_trim(self):
        updated = 0
        for box_cells in self.boxes:
            num_positions = {n: [] for n in range(1, self.width + 1)}

            for (r, c) in box_cells:
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))

            for n, cells in num_positions.items():
                if len(cells) == 1:
                    r, c = cells[0]
                    if self.possible_values_cache[(r, c)] != {n}:
                        updated += len(self.possible_values_cache[(r, c)]) - 1
                        self.possible_values_cache[(r, c)] = {n}

                rows = {r for r, _ in cells}
                cols = {c for _, c in cells}

                if len(rows) == 1:
                    row = rows.pop()
                    for c in range(self.width):
                        if (row, c) not in box_cells and (row, c) in self.possible_values_cache:
                            if n in self.possible_values_cache[(row, c)]:
                                self.possible_values_cache[(row, c)].remove(n)
                                updated += 1

                if len(cols) == 1:
                    col = cols.pop()
                    for r in range(self.height):
                        if (r, col) not in box_cells and (r, col) in self.possible_values_cache:
                            if n in self.possible_values_cache[(r, col)]:
                                self.possible_values_cache[(r, col)].remove(n)
                                updated += 1
        return updated
    
    def trim_naked_subsets(self):
        updated = 0
        Kmax =self.Kmax
        # -------- General naked k-subsets (rows) --------
        for r in range(self.height):
            unit_cells = [
                (r, c) for c in range(self.width)
                if (r, c) in self.possible_values_cache
            ]

            for k in range(1, min(Kmax, len(unit_cells)) + 1):
                candidates = [
                    cell for cell in unit_cells
                    if 1 <= len(self.possible_values_cache[cell]) <= k
                ]

                for combo in combinations(candidates, k):
                    union_vals = set().union(
                        *(self.possible_values_cache[cell] for cell in combo)
                    )
                    if len(union_vals) == k:
                        for cell in unit_cells:
                            if cell not in combo:
                                before = set(self.possible_values_cache[cell])
                                after = before - union_vals
                                if after != before:
                                    self.possible_values_cache[cell] = after
                                    updated += 1

        # -------- General naked k-subsets (columns) --------
        for c in range(self.width):
            unit_cells = [
                (r, c) for r in range(self.height)
                if (r, c) in self.possible_values_cache
            ]

            for k in range(1, min(Kmax, len(unit_cells)) + 1):
                candidates = [
                    cell for cell in unit_cells
                    if 1 <= len(self.possible_values_cache[cell]) <= k
                ]

                for combo in combinations(candidates, k):
                    union_vals = set().union(
                        *(self.possible_values_cache[cell] for cell in combo)
                    )
                    if len(union_vals) == k:
                        for cell in unit_cells:
                            if cell not in combo:
                                before = set(self.possible_values_cache[cell])
                                after = before - union_vals
                                if after != before:
                                    self.possible_values_cache[cell] = after
                                    updated += 1
        return updated
    def trim_singles(self):
        updated = 0
        for r in range(self.height):
            num_positions = {n: [] for n in range(1, self.width + 1)}
            for c in range(self.width):
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))
            for k,x in num_positions.items():
                if len(x)==1:
                    cell = x[0]
                    if self.possible_values_cache[cell] != {k}:
                        self.possible_values_cache[cell] = {k}
                        updated += 1
        for c in range(self.width):
            num_positions = {n: [] for n in range(1, self.width + 1)}
            for r in range(self.height):
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))
            for k,x in num_positions.items():
                if len(x)==1:
                    cell = x[0]
                    if self.possible_values_cache[cell] != {k}:
                        self.possible_values_cache[cell] = {k}
                        updated += 1
        return updated

    def possible_values_trim(self):
        updated = 0
        if not self.trim_is_overkill:
            updated += self.trim_singles()
            updated += self.trim_naked_subsets()
        if self.subtable_type == "regular":
            updated += self.regular_table_trim()
        elif self.subtable_type =="irregular":
            updated += self.irregular_table_trim()
        # print(f"Possible values trimmed, {updated} updates made.")
        return updated
    
    def solve(self):
        def solve_sudoku(cell_idx=0):
            if cell_idx >= len(self.cells_to_fill):
                return True
            self.possible_values_cache.clear()
            sorted_cells = sorted(self.cells_to_fill[cell_idx:], key=lambda x: len(self.possible_values(x[0], x[1])))
            self.cells_to_fill[cell_idx:] = sorted_cells
            while self.possible_values_trim():
                pass
            sorted_cells = sorted(self.cells_to_fill[cell_idx:], key=lambda x: len(self.possible_values_extended(x[0], x[1])))
            self.cells_to_fill[cell_idx:] = sorted_cells
                # print(f"At cell_idx {cell_idx}, {len(self.cells_to_fill) - cell_idx} cells left to fill.")
            i, j = self.cells_to_fill[cell_idx]
            if self.board[i][j] != 0:
                return solve_sudoku(cell_idx + 1)
            # print(self.possible_values_cache)
            pos_lst =list(self.possible_values_cache[(i,j)])
            for num in pos_lst:
                if self.is_valid(num, i, j):
                    self.board[i][j] = num
                    if solve_sudoku(cell_idx + 1):
                        return True
                    self.board[i][j] = 0
            return False

        solve_sudoku()
        # print(self.board)

        return self.board
    