from .solver import BaseSolver
import random 

class SudokuSolver(BaseSolver):
    def solve(self):
        # Implement a simple backtracking algorithm for Sudoku
        board = self.info["table"]
        possible_values_cache = {}
        cells_to_fill = []
        for i in range(self.info["height"]):
            for j in range(self.info["width"]):
                if board[i][j] == 0:
                    cells_to_fill.append((i, j))

        def is_valid(num, row, col):
            for x in range(self.info["width"]):
                if board[row][x] == num:
                    return False
            for x in range(self.info["height"]):
                if board[x][col] == num:
                    return False
            start_row, start_col = self.info["subtable_height"] * (row // self.info["subtable_height"]), self.info["subtable_width"] * (col // self.info["subtable_width"])
            for i in range(self.info["subtable_height"]):
                for j in range(self.info["subtable_width"]):
                    if board[start_row + i][start_col + j] == num:
                        return False
            return True

        def possible_values(row, col):
            values = set(range(1, self.info["width"] + 1))
            for x in range(self.info["width"]):
                if board[row][x] in values:
                    values.remove(board[row][x])
            for x in range(self.info["height"]):
                if board[x][col] in values:
                    values.remove(board[x][col])
            start_row, start_col = self.info["subtable_height"] * (row // self.info["subtable_height"]), self.info["subtable_width"] * (col // self.info["subtable_width"])
            for r in range(self.info["subtable_height"]):
                for c in range(self.info["subtable_width"]):
                    if board[start_row + r][start_col + c] in values:
                        values.remove(board[start_row + r][start_col + c])
            possible_values_cache[(row, col)] = values
            return list(values)
        

        def possible_values_extended(row, col):
            values = possible_values_cache[(row, col)]
            return list(values)
        
        def possible_values_trim():
            updated = 0
            for box_row in range(self.info["height"] // self.info["subtable_height"]):
                for box_col in range(self.info["width"] // self.info["subtable_width"]):
                    # box start indices
                    r0 = box_row * self.info["subtable_height"]
                    c0 = box_col * self.info["subtable_width"]

                    # collect candidates in this box
                    num_positions = {n: [] for n in range(1, self.info["width"] + 1)}

                    for r in range(r0, r0 + self.info["subtable_height"]):
                        for c in range(c0, c0 + self.info["subtable_width"]):
                            if (r, c) in possible_values_cache:
                                for n in possible_values_cache[(r, c)]:
                                    num_positions[n].append((r, c))

                    # analyze each number
                    for n, cells in num_positions.items():
                        if len(cells) == 0:
                            continue
                        if len(cells) == 1:
                            r, c = cells[0]
                            if (r, c) in possible_values_cache and n in possible_values_cache[(r, c)]:
                                updated += len(possible_values_cache[(r, c)])-1
                                possible_values_cache[(r, c)] = {n}
                            continue

                        rows = {r for r, _ in cells}
                        cols = {c for _, c in cells}

                        # Row restriction
                        if len(rows) == 1:
                            row = rows.pop()
                            for c in range(self.info["width"]):
                                if not (c0 <= c < c0 + self.info["subtable_width"]):
                                    if (row, c) in possible_values_cache and n in possible_values_cache[(row, c)]:
                                        possible_values_cache[(row, c)].remove(n)
                                        updated +=1

                        # Column restriction
                        if len(cols) == 1:
                            col = cols.pop()
                            for r in range(self.info["height"]):
                                if not (r0 <= r < r0 + self.info["subtable_height"]):
                                    if (r, col) in possible_values_cache and n in possible_values_cache[(r, col)]:
                                        possible_values_cache[(r, col)].remove(n)
                                        updated +=1
            # print(f"Possible values trimmed, {updated} updates made.")
            return updated
        
        def solve_sudoku(cell_idx=0):
            if cell_idx >= len(cells_to_fill):
                return True
            if cell_idx % 5 == 0:
                possible_values_cache.clear()
                sorted_cells = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values(x[0], x[1])))
                cells_to_fill[cell_idx:] = sorted_cells
                while possible_values_trim():
                    pass
                sorted_cells = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values_extended(x[0], x[1])))
                cells_to_fill[cell_idx:] = sorted_cells
                # print(f"At cell_idx {cell_idx}, {len(cells_to_fill) - cell_idx} cells left to fill.")
            i, j = cells_to_fill[cell_idx]
            if board[i][j] != 0:
                return solve_sudoku(cell_idx + 1)
            # print(possible_values_cache)
            for num in possible_values_cache.get((i, j), range(1, self.info["width"] + 1)):
                if is_valid(num, i, j):
                    board[i][j] = num
                    if solve_sudoku(cell_idx + 1):
                        return True
                    board[i][j] = 0
            return False

        solve_sudoku()
        # print(board)

        return board
    