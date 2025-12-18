from .solver import BaseSolver
from copy import copy, deepcopy
import random 

class StarBattleSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.boxes=info["boxes"]
        self.boxes_table = self.info["boxes_table"]
        self.stars = self.info["items_per_box"]
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.filling_boxes_cache={}
    def encode(self):
        v=[]
        for a in self.board:
            x=1
            s=0
            for b in a:
                s+=b*x
                x*=3
            v.append(s)
        return tuple(v)

    def count_row(self, i):
        return sum(self.board[i][j]==2 for j in range(self.width))

    def count_col(self, j):
        return sum(self.board[i][j]==2 for i in range(self.height))

    def count_box(self, v):
        return sum(self.board[i][j]==2 for i, j in self.boxes[v])

    def has_adjacent_star(self, i, j):
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < self.height and 0 <= nj < self.width:
                    if self.board[ni][nj] == 2:
                        return True
        return False
    
    def print_board(self):
        for i in range(self.height):
            for j in range(self.width):
                print(self.board[i][j],end="|" if (j!=self.width-1 and self.boxes_table[i][j] != self.boxes_table[i][j+1]) else " ")
            print()
            if i==self.height-1:
                continue
            for j in range(self.width):
                print(" " if self.boxes_table[i][j] == self.boxes_table[i+1][j] else "-" , end=" ")
            print()

    def max_non_adjacent_1d(self, positions):
        # positions: sorted list of indices
        if not positions:
            return 0

        count = 1
        last = positions[0]

        for p in positions[1:]:
            if p > last + 1:
                count += 1
                last = p

        return count
    def max_non_adjacent_2d(self, cells):
        cells = set(cells)
        used = set()
        count = 0

        for i, j in cells:
            if (i, j) in used:
                continue

            # 4 possible 2x2 blocks containing (i,j)
            blocks = []
            for bi, bj in (
                (i - 1, j - 1),
                (i - 1, j),
                (i, j - 1),
                (i, j),
            ):
                block = {
                    (bi + di, bj + dj)
                    for di in (0, 1)
                    for dj in (0, 1)
                }
                blocks.append(block)

            # choose block covering max remaining cells
            best_block = max(
                blocks,
                key=lambda b: len((b & cells) - used)
            )

            if not ((best_block & cells) - used):
                continue

            count += 1
            used |= best_block

        return count

    
    def box_feasible(self, v):
        stars = self.count_box(v)
        if stars > self.stars:
            return False

        candidates = [
            (i, j) for (i, j) in self.boxes[v]
            if self.board[i][j] == 0 and self.can_place_star(i, j)
        ]

        return stars + self.max_non_adjacent_2d(candidates) >= self.stars
    
    def fill_all_boxes(self):
        key=self.encode()
        updates=key not in self.filling_boxes_cache
        while updates:
            updates = False
            for i in range(self.height):
                for j in range(self.width):
                    if self.board[i][j]!=0:
                        continue
                    if not self.can_place_star(i,j) or not self.test_place_star(i,j):
                        if self.cant_place_empty(i,j) or not self.test_place_empty(i,j):
                            self.filling_boxes_cache[key]=False
                            return False
                        updates= True
                        self.board[i][j]=1
                    elif self.cant_place_empty(i,j) or not self.test_place_empty(i,j):
                        updates= True
                        self.board[i][j]=2
        if key in self.filling_boxes_cache:
            if not self.filling_boxes_cache[key]:
                return False
            self.board= deepcopy(self.filling_boxes_cache[key])
        else:
            self.filling_boxes_cache[key] =deepcopy(self.board)
        return True

    def all_boxes_feasible(self):
        for v in range(len(self.boxes)):
            if not self.box_feasible(v):
                return False
        #check the columns
        for i in range(self.width-1):
            candidates = []
            stars = 0
            for j in range(self.height):
                if self.board[j][i]==2:
                    stars+=1
                elif self.board[j][i]==0 and self.can_place_star(j, i):
                    candidates.append((j,i))
                if self.board[j][i+1]==2:
                    stars+=1
                elif self.board[j][i+1]==0 and self.can_place_star(j,i+1):
                    candidates.append((j,i+1))
            if stars > self.stars * 2:
                return False
            if stars + self.max_non_adjacent_2d(candidates) < self.stars *2:
                return False
        for i in range(self.height-1):
            candidates = []
            stars = 0
            for j in range(self.width):
                if self.board[i][j]==2:
                    stars+=1
                elif self.board[i][j]==0 and self.can_place_star(i,j):
                    candidates.append((i,j))
            for j in range(self.width):
                if self.board[i+1][j]==2:
                    stars+=1
                elif self.board[i+1][j]==0 and self.can_place_star(i+1,j):
                    candidates.append((i+1,j))
            if stars > self.stars * 2:
                return False
            if stars + self.max_non_adjacent_2d(candidates) < self.stars *2:
                return False   
        return True
    
    def test_place_star(self, i, j):
        board_copy=deepcopy(self.board)
        self.board[i][j] = 2
        v=self.all_boxes_feasible()
        self.board=board_copy
        return v

    def test_place_empty(self, i, j):
        board_copy=deepcopy(self.board)
        self.board[i][j] = 1
        v=self.all_boxes_feasible()
        self.board=board_copy
        return v

    def can_place_star(self, i, j):
        if self.board[i][j] == 2:
            return False
        if self.has_adjacent_star(i, j):
            return False
        if self.count_row(i) >= self.stars:
            return False
        if self.count_col(j) >= self.stars:
            return False
        if self.count_box(self.boxes_table[i][j]) >= self.stars:
            return False
        return True

    def cant_place_empty(self, i, j):
        # ---- Row ----
        stars = self.count_row(i)
        candidates = [
            jj for jj in range(self.width)
            if jj != j and self.board[i][jj] == 0 and self.can_place_star(i, jj)
        ]
        if stars + self.max_non_adjacent_1d(sorted(candidates)) < self.stars:
            return True

        # ---- Column ----
        stars = self.count_col(j)
        candidates = [
            ii for ii in range(self.height)
            if ii != i and self.board[ii][j] == 0 and self.can_place_star(ii, j)
        ]
        if stars + self.max_non_adjacent_1d(sorted(candidates)) < self.stars:
            return True

        # ---- Box ----
        box = self.boxes_table[i][j]
        stars = self.count_box(box)
        candidates = [
            (ii, jj) for ii, jj in self.boxes[box]
            if (ii, jj) != (i, j) and self.board[ii][jj] == 0 and self.can_place_star(ii, jj)
        ]
        if stars + self.max_non_adjacent_2d(candidates) < self.stars:
            return True

        return False

    # ---------------------------
    # Backtracking solver
    # ---------------------------

    def solve_puzzle(self, cell_idx=0):
        if cell_idx == self.height * self.width:
            return self.is_complete()
        i, j = self.cells_order[cell_idx]
        if self.board[i][j]!=0:
            return self.solve_puzzle(cell_idx + 1)
        if not self.all_boxes_feasible():
            return False
        if not self.fill_all_boxes():
            return False
        if self.board[i][j]!=0:
            return self.solve_puzzle(cell_idx + 1)
        self.cells_order[cell_idx:] = sorted(self.cells_order[cell_idx:],key=lambda x:sum(self.board[v[0]][v[1]]==0 for v in self.boxes[self.boxes_table[x[0]][x[1]]]))
        
        print(cell_idx,i,j)
        self.print_board()
        # Try placing a star
        board_save=deepcopy(self.board)
        if self.can_place_star(i, j):
            self.board[i][j] = 2
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.height and 0 <= nj < self.width:
                        self.board[ni][nj] = 1 
            if self.solve_puzzle(cell_idx + 1):
                return True
            self.board=board_save

        if self.cant_place_empty(i,j):
            return False
        print(cell_idx,i,j, "flling with 1 instead")
        self.board[i][j] = 1
        return self.solve_puzzle(cell_idx + 1)

    # ---------------------------
    # Final validation
    # ---------------------------

    def is_complete(self):
        for i in range(self.height):
            if self.count_row(i) != self.stars:
                return False
        for j in range(self.width):
            if self.count_col(j) != self.stars:
                return False
        for v in range(len(self.boxes)):
            if self.count_box(v) != self.stars:
                return False
        return True

    # ---------------------------
    # Entry point
    # ---------------------------

    def solve(self):
        self.cells_order = [(i,j) for i in range(self.height) for j in range(self.width)]
        
        self.cells_order = sorted(self.cells_order,key=lambda x:sum(self.board[v[0]][v[1]]==0 for v in self.boxes[self.boxes_table[x[0]][x[1]]]))
        if self.solve_puzzle():
            return self.board
        return None