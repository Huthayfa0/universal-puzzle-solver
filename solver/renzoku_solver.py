from .solver import BaseSolver

class RenzokuSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.board = self.info["table"]
        self.cell_info = self.info["cell_info_table"]
        self.all_dir = [(1,0),(-1,0),(0,1),(0,-1)]


    def solve(self):
        # Implement a simple backtracking algorithm for Renzoku
        possible_values_cache = {}
        cells_to_fill = []
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 0:
                    cells_to_fill.append((i, j))

        def is_valid(num, row, col):
            for x in range(self.width):
                if self.board[row][x] == num:
                    return False
            for x in range(self.height):
                if self.board[x][col] == num:
                    return False
            for v in self.cell_info[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0 and abs(self.board[row+v[0]][col+v[1]]-num)>1:
                    return False
            for v in self.all_dir:
                if v not in self.cell_info[row][col] and 0<=row+v[0]<self.height and 0<=col + v[1] <self.width:
                    if self.board[row+v[0]][col+v[1]]!=0 and abs(self.board[row+v[0]][col+v[1]]-num)<=1:
                        return False
            return True

        def possible_values(row, col):
            values = set(range(1, self.width + 1))
            for x in range(self.width):
                if self.board[row][x] in values:
                    values.remove(self.board[row][x])
            for x in range(self.height):
                if self.board[x][col] in values:
                    values.remove(self.board[x][col])
            for v in self.cell_info[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0:
                    values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)==1 }
            for v in self.all_dir:
                if v not in self.cell_info[row][col] and 0<=row+v[0]<self.height and 0<=col + v[1] <self.width:
                    if self.board[row+v[0]][col+v[1]]!=0:
                        values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)>1 }
            
            possible_values_cache[(row, col)] = values
            return list(values)
        

        def possible_values_extended(row, col):
            values = possible_values_cache[(row, col)]
            return list(values)
        
        def possible_values_trim():
            updated = 0
            for i, j in possible_values_cache.keys():
                to_remv = set()
                if self.board[i][j]!=0:
                    continue
                for n in possible_values_cache[(i, j)]:

                    for v in self.cell_info[i][j]:
                        lst = possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                        if n+1 not in lst and n-1 not in lst:
                            to_remv.add(n)
                    for v in self.all_dir:
                        if v not in self.cell_info[i][j] and 0<=i+v[0]<self.height and 0<=j + v[1] <self.width:
                            lst = possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                            if all(abs(x-n)<=1 for x in lst):
                                to_remv.add(n)
                updated+=len(to_remv)
                possible_values_cache[(i, j)]-=to_remv
            
            # print(f"Possible values trimmed, {updated} updates made.")
            return updated
        
        def solve_renzoku(cell_idx=0):
            if cell_idx >= len(cells_to_fill):
                return True
            possible_values_cache.clear()
            cells_to_fill[cell_idx:] = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values(x[0], x[1])))
            while possible_values_trim():
                pass
            cells_to_fill[cell_idx:] = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values_extended(x[0], x[1])))
                # print(f"At cell_idx {cell_idx}, {len(cells_to_fill) - cell_idx} cells left to fill.")
            i, j = cells_to_fill[cell_idx]
            if self.board[i][j] != 0:
                return solve_renzoku(cell_idx + 1)
            # print(possible_values_cache)
            for num in possible_values_cache.get((i, j), range(1, self.width + 1)):
                if is_valid(num, i, j):
                    self.board[i][j] = num
                    if solve_renzoku(cell_idx + 1):
                        return True
                    self.board[i][j] = 0
            return False

        solve_renzoku()
        print(self.board)

        return self.board
    