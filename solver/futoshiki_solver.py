from .sudoku_solver import SudokuSolver
class FutoshikiSolver(SudokuSolver):
    def __init__(self, info):
        super().__init__(info)
        self.trim_is_overkill = False
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

    def is_valid(self, num, row, col):
        if not super().is_valid(num, row, col):
            return False
        for v in self.adj_more[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0 and self.board[row+v[0]][col+v[1]]>=num:
                return False
        for v in self.adj_less[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0 and self.board[row+v[0]][col+v[1]]<=num:
                return False
        return True
    
    def possible_values(self, row, col):
        values = set(super().possible_values(row, col))
        for v in self.adj_more[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0:
                values = {c for c in values if self.board[row+v[0]][col+v[1]]<c}
        for v in self.adj_less[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0:
                values = {c for c in values if self.board[row+v[0]][col+v[1]]>c }
        
        self.possible_values_cache[(row, col)] = values
        return list(values)
    
    def possible_values_trim(self):
        updated = super().possible_values_trim()
        #apply the more and less condition on the possiblities
        for i, j in self.possible_values_cache.keys():
            
            to_remv = set()
            if self.board[i][j]!=0:
                continue
            for n in self.possible_values_cache[(i, j)]:
                for v in self.adj_more[i][j]:
                    lst = self.possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                    if not lst:
                        lst = [1]
                    if n<=min(lst):
                        to_remv.add(n)
                for v in self.adj_less[i][j]:
                    lst = self.possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                    if not lst:
                        lst = [self.height]
                    if n>=max(lst):
                        to_remv.add(n)
            updated+=len(to_remv)
            self.possible_values_cache[(i, j)]-=to_remv
        
        # print(f"Possible values trimmed, {updated} updates made.")
        return updated
    