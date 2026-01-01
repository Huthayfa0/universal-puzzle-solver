from .solver import BaseSolver

class KakurasuSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.row_info = self.info["horizontal_borders"]
        self.col_info = self.info["vertical_borders"]
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def possible_values_line(self, arr,val,sum_emp=None,index=0):
        if val < 0 or (sum_emp is not None and sum_emp < 0):
            return []
        if sum_emp is None:
            sum_emp = len(arr)*(len(arr)+1)//2 - val
        results = []
        if index >= len(arr):
            if val == 0 and sum_emp == 0:
                results.append(arr.copy())
            return results
        if arr[index]==1:
            return self.possible_values_line(arr, val - (index + 1), sum_emp, index + 1)
        elif arr[index]==2:
            return self.possible_values_line(arr, val, sum_emp - (index + 1), index + 1)
        arr[index] = 1
        results.extend(self.possible_values_line(arr, val - (index + 1), sum_emp, index + 1))
        arr[index] = 2
        results.extend(self.possible_values_line(arr, val, sum_emp - (index + 1), index + 1))
        arr[index] = 0
        return results
    
    def common_values_line(self,arr, val):
        possible_lines = self.possible_values_line(arr.copy(), val)
        # print ("Possible lines:", possible_lines, "for val", val, "and arr", arr)
        if not possible_lines:
            return None
        common = [possible_lines[0][i] for i in range(len(arr))]
        for line in possible_lines[1:]:
            for i in range(len(arr)):
                if common[i] != line[i]:
                    common[i] = 0
        return common

    def submit_common(self):
        updated = 0
            # Check rows
        for i in range(self.height):
            common = self.common_values_line(self.board[i], self.row_info[i])
            if common is not None:
                for j in range(self.width):
                    if common[j] != 0 and self.board[i][j] != common[j]:
                        self.board[i][j] = common[j]
                        updated += 1
        # Check columns
        for j in range(self.width):
            col = [self.board[i][j] for i in range(self.height)]
            common = self.common_values_line(col, self.col_info[j])
            if common is not None:
                for i in range(self.height):
                    if common[i] != 0 and self.board[i][j] != common[i]:
                        self.board[i][j] = common[i]
                        updated += 1
        return updated
    
    def is_valid(self):
        # Check row sums
        for i in range(self.height):
            if sum((j + 1) * (self.board[i][j]==1) for j in range(self.width)) != self.row_info[i]:
                return False
        # Check column sums
        for j in range(self.width):
            if sum((i + 1) * (self.board[i][j]==1) for i in range(self.height)) != self.col_info[j]:
                return False
        return True

    def solve_puzzle(self, cell_idx=0):
        if cell_idx >= self.height * self.width:
            return self.is_valid()
        i, j = divmod(cell_idx, self.width)
        if self.board[i][j]==0:
            return self.solve_puzzle(cell_idx + 1)
        for value in [1, 2]:
            self.board[i][j] = value
            if self.solve_puzzle(cell_idx + 1):
                return True
            self.board[i][j] = 0
        return False
    
    def solve(self):
        s = self.submit_common()
        while s > 0:
            print(s)
            s = self.submit_common()
        # self.solve_puzzle() ## surprisingly not needed
        print(self.board)
        return self.board
