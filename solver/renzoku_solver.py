from .solver import BaseSolver
from itertools import combinations
class RenzokuSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.board = self.info["table"]
        self.adj_dot = [[] for _ in range(self.height)]
        self.adj_ndot = [[] for _ in range(self.height)]
        self.all_dir = {(1,0),(-1,0),(0,1),(0,-1)}
        for i in range(self.height):
            self.adj_dot[i]=self.info["cell_info_table"][i]
            self.adj_ndot[i] = [[] for _ in range(self.width)]
            for j in range(self.width):
                self.adj_ndot[i][j] = [a for a in self.all_dir-set(self.info["cell_info_table"][i][j]) if 0<=a[0]+i<self.height and 0<=a[1]+j<self.width]
            


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
            for v in self.adj_dot[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0 and abs(self.board[row+v[0]][col+v[1]]-num)>1:
                    return False
            for v in self.adj_ndot[row][col]:
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
            for v in self.adj_dot[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0:
                    values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)==1 }
            for v in self.adj_ndot[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0:
                    values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)>1 }
            
            possible_values_cache[(row, col)] = values
            return list(values)
        

        def possible_values_extended(row, col):
            values = possible_values_cache[(row, col)]
            return list(values)
        
        def possible_values_trim():
            updated = 0

            # hidden singles (rows)
            for r in range(self.height):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for c in range(self.width):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for n, cells in num_positions.items():
                    if len(cells) == 1:
                        cell = cells[0]
                        if possible_values_cache[cell] != {n}:
                            possible_values_cache[cell] = {n}
                            updated += 1

            # hidden singles (columns)
            for c in range(self.width):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for r in range(self.height):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for n, cells in num_positions.items():
                    if len(cells) == 1:
                        cell = cells[0]
                        if possible_values_cache[cell] != {n}:
                            possible_values_cache[cell] = {n}
                            updated += 1

            # naked subsets (rows & columns)
            Kmax = 6

            for r in range(self.height):
                unit = [(r, c) for c in range(self.width) if (r, c) in possible_values_cache]
                for k in range(1, min(Kmax, len(unit)) + 1):
                    for combo in combinations(unit, k):
                        union_vals = set().union(*(possible_values_cache[x] for x in combo))
                        if len(union_vals) == k:
                            for cell in unit:
                                if cell not in combo:
                                    before = set(possible_values_cache[cell])
                                    after = before - union_vals
                                    if after != before:
                                        possible_values_cache[cell] = after
                                        updated += 1

            for c in range(self.width):
                unit = [(r, c) for r in range(self.height) if (r, c) in possible_values_cache]
                for k in range(1, min(Kmax, len(unit)) + 1):
                    for combo in combinations(unit, k):
                        union_vals = set().union(*(possible_values_cache[x] for x in combo))
                        if len(union_vals) == k:
                            for cell in unit:
                                if cell not in combo:
                                    before = set(possible_values_cache[cell])
                                    after = before - union_vals
                                    if after != before:
                                        possible_values_cache[cell] = after
                                        updated += 1

            for i, j in possible_values_cache.keys():
                to_remv = set()
                if self.board[i][j]!=0:
                    continue
                for n in possible_values_cache[(i, j)]:

                    for v in self.adj_dot[i][j]:
                        lst = possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                        if n+1 not in lst and n-1 not in lst:
                            to_remv.add(n)
                    for v in self.adj_ndot[i][j]:
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
    