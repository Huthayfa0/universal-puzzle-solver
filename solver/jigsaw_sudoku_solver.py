from .solver import BaseSolver

class JigsawSudokuSolver(BaseSolver):
    def solve(self):
        # Implement a simple backtracking algorithm for Sudoku
        board = self.info["table"]
        boxes = self.info["boxes"] #dict oft he indecies of each box
        boxes_table = self.info["boxes_table"] #the box in each cell
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
            box_id = boxes_table[row][col]
            for r, c in boxes[box_id]:
                if board[r][c] == num:
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
            box_id = boxes_table[row][col]
            for r, c in boxes[box_id]:
                if board[r][c] in values:
                    values.remove(board[r][c])
            possible_values_cache[(row, col)] = values
            return list(values)
        

        def possible_values_extended(row, col):
            values = possible_values_cache[(row, col)]
            return list(values)
        
        def possible_values_trim():
            updated = 0
            for box_cells in boxes:
                num_positions = {n: [] for n in range(1, self.info["width"] + 1)}

                for (r, c) in box_cells:
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))

                for n, cells in num_positions.items():
                    if len(cells) == 1:
                        r, c = cells[0]
                        if possible_values_cache[(r, c)] != {n}:
                            updated += len(possible_values_cache[(r, c)]) - 1
                            possible_values_cache[(r, c)] = {n}

                    rows = {r for r, _ in cells}
                    cols = {c for _, c in cells}

                    if len(rows) == 1:
                        row = rows.pop()
                        for c in range(self.info["width"]):
                            if (row, c) not in box_cells and (row, c) in possible_values_cache:
                                if n in possible_values_cache[(row, c)]:
                                    possible_values_cache[(row, c)].remove(n)
                                    updated += 1

                    if len(cols) == 1:
                        col = cols.pop()
                        for r in range(self.info["height"]):
                            if (r, col) not in box_cells and (r, col) in possible_values_cache:
                                if n in possible_values_cache[(r, col)]:
                                    possible_values_cache[(r, col)].remove(n)
                                    updated += 1
            
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
    