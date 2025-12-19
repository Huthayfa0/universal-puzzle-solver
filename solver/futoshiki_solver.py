from .solver import BaseSolver
import random
class FutoshikiSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.board = self.info["table"]
        self.adj_more = [[] for _ in range(self.height)]
        self.adj_less = [[] for _ in range(self.height)]
        self.mx_idx = -1
        for i in range(self.height):
            self.adj_more[i]=self.info["cell_info_table"][i]
            self.adj_less[i] = [[] for _ in range(self.width)]
        for i in range(self.height):
            for j in range(self.width):
                for a in self.info["cell_info_table"][i][j]:
                    self.adj_less[i+a[0]][j+a[1]].append((-a[0],-a[1])) 

    def solve(self):
        # Implement a simple backtracking algorithm for Futoshiki
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
            for v in self.adj_more[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0 and self.board[row+v[0]][col+v[1]]>=num:
                    return False
            for v in self.adj_less[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0 and self.board[row+v[0]][col+v[1]]<=num:
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
            for v in self.adj_more[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0:
                    values = {c for c in values if self.board[row+v[0]][col+v[1]]<c}
            for v in self.adj_less[row][col]:
                if self.board[row+v[0]][col+v[1]]!=0:
                    values = {c for c in values if self.board[row+v[0]][col+v[1]]>c }
            
            possible_values_cache[(row, col)] = values
            return list(values)
        

        def possible_values_extended(row, col):
            values = possible_values_cache[(row, col)]
            return list(values)
        
        def possible_values_trim():
            updated = 0
            for r in range(self.height):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for c in range(self.width):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for k,x in num_positions.items():
                    if len(x)==1:
                        cell = x[0]
                        if possible_values_cache[cell] != {k}:
                            possible_values_cache[cell] = {k}
                            updated += 1
                            

            for c in range(self.width):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for r in range(self.height):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for k,x in num_positions.items():
                    if len(x)==1:
                        cell = x[0]
                        if possible_values_cache[cell] != {k}:
                            possible_values_cache[cell] = {k}
                            updated += 1
            for r in range(self.height):
                pairs = {}
                for c in range(self.width):
                    if (r, c) in possible_values_cache and len(possible_values_cache[(r, c)]) == 2:
                        pair = tuple(sorted(possible_values_cache[(r, c)]))
                        if pair in pairs:
                            for cc in range(self.width):
                                if cc != c and cc != pairs[pair] and (r, cc) in possible_values_cache:
                                    if pair[0] in possible_values_cache[(r, cc)] or pair[1] in possible_values_cache[(r, cc)]:
                                        possible_values_cache[(r, cc)] -= set(pair)
                                        updated += 1
                        else:
                            pairs[pair] = c
            for c in range(self.width):
                pairs = {}
                for r in range(self.height):
                    if (r, c) in possible_values_cache and len(possible_values_cache[(r, c)]) == 2:
                        pair = tuple(sorted(possible_values_cache[(r, c)]))
                        if pair in pairs:
                            for rr in range(self.height):
                                if rr != r and rr != pairs[pair] and (rr, c) in possible_values_cache:
                                    if pair[0] in possible_values_cache[(rr, c)] or pair[1] in possible_values_cache[(rr, c)]:
                                        possible_values_cache[(rr, c)] -= set(pair)
                                        updated += 1
                        else:
                            pairs[pair] = r

            for i, j in possible_values_cache.keys():
                
                to_remv = set()
                if self.board[i][j]!=0:
                    continue
                for n in possible_values_cache[(i, j)]:

                    for v in self.adj_more[i][j]:
                        lst = possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                        if not lst:
                            lst = [1]
                        if n<=min(lst):
                            to_remv.add(n)
                    for v in self.adj_less[i][j]:
                        lst = possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                        if not lst:
                            lst = [self.height]
                        if n>=max(lst):
                            to_remv.add(n)
                updated+=len(to_remv)
                possible_values_cache[(i, j)]-=to_remv
            
            # print(f"Possible values trimmed, {updated} updates made.")
            return updated
        def solve_futoshiki(cell_idx=0):
            if cell_idx >= len(cells_to_fill):
                return True
            i, j = cells_to_fill[cell_idx]
            if self.board[i][j] != 0:
                return solve_futoshiki(cell_idx + 1)
            if len(possible_values_cache.get((i, j), range(1, self.width + 1)))>1:
                possible_values_cache.clear()
                cells_to_fill[cell_idx:] = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values(x[0], x[1])))
                while possible_values_trim():
                    pass
                cells_to_fill[cell_idx:] = sorted(cells_to_fill[cell_idx:], key=lambda x: len(possible_values_extended(x[0], x[1])))
                # print(f"At cell_idx {cell_idx}, {len(cells_to_fill) - cell_idx} cells left to fill.")
            i, j = cells_to_fill[cell_idx]
            if self.board[i][j] != 0:
                return solve_futoshiki(cell_idx + 1)
            
            # print(possible_values_cache)
            pos_lst =list(possible_values_cache.get((i, j), range(1, self.width + 1)))
            if len(pos_lst)>1:
                print(cell_idx,i,j)
                print(list(pos_lst))
            for num in pos_lst:
                if is_valid(num, i, j):
                    # if self.mx_idx-cell_idx >60 and len(pos_lst)>1 and num==pos_lst[1]:
                    #     print(cell_idx,i,j,self.mx_idx)
                    #     return True
                    self.board[i][j] = num
                    
                    if solve_futoshiki(cell_idx + 1):
                        return True
                    self.board[i][j] = 0
            return False

        solve_futoshiki()
        print(self.board)

        return self.board
    