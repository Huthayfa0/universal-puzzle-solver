from .sudoku_solver import SudokuSolver
from itertools import combinations
class RenzokuSolver(SudokuSolver):
    def __init__(self, info):
        super().__init__(info)
        self.trim_is_overkill = False
        self.adj_dot = [[] for _ in range(self.height)]
        self.adj_ndot = [[] for _ in range(self.height)]
        self.all_dir = {(1,0),(-1,0),(0,1),(0,-1)}
        for i in range(self.height):
            self.adj_dot[i]=self.info["cell_info_table"][i]
            self.adj_ndot[i] = [[] for _ in range(self.width)]
            for j in range(self.width):
                self.adj_ndot[i][j] = [a for a in self.all_dir-set(self.info["cell_info_table"][i][j]) if 0<=a[0]+i<self.height and 0<=a[1]+j<self.width]
            
    def is_valid(self, num, row, col):
        if not super().is_valid(num, row, col):
            return False
        for v in self.adj_dot[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0 and abs(self.board[row+v[0]][col+v[1]]-num)>1:
                return False
        for v in self.adj_ndot[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0 and abs(self.board[row+v[0]][col+v[1]]-num)<=1:
                return False
        return True

    def possible_values(self, row, col):
        values = set(super().possible_values(row, col))
        for v in self.adj_dot[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0:
                values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)==1 }
        for v in self.adj_ndot[row][col]:
            if self.board[row+v[0]][col+v[1]]!=0:
                values = {c for c in values if abs(self.board[row+v[0]][col+v[1]]-c)>1 }
        
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

                for v in self.adj_dot[i][j]:
                    lst = self.possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                    if n+1 not in lst and n-1 not in lst:
                        to_remv.add(n)
                for v in self.adj_ndot[i][j]:
                    lst = self.possible_values_cache.get((i+v[0],j+v[1]),{self.board[i+v[0]][j+v[1]]})
                    if all(abs(x-n)<=1 for x in lst):
                        to_remv.add(n)
            updated+=len(to_remv)
            self.possible_values_cache[(i, j)]-=to_remv
        
        # print(f"Possible values trimmed, {updated} updates made.")
        return updated
    