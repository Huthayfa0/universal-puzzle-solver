from .solver import BaseSolver
import random 

class KakurasuSolver(BaseSolver):
    def solve(self):
        row_sums = self.info["horizontal_borders"]
        col_sums = self.info["vertical_borders"]
        height = self.info["height"]
        width = self.info["width"]
        board = [[0 for _ in range(width)] for _ in range(height)]

        def possible_values_line(arr,sum,sum_emp=None,index=0):
            if sum < 0 or (sum_emp is not None and sum_emp < 0):
                return []
            if sum_emp is None:
                sum_emp = len(arr)*(len(arr)+1)//2 - sum
            # print(f"Calculating possible values for arr {arr} with sum {sum} and sum_emp {sum_emp} at index {index}")
            results = []
            if index >= len(arr):
                if sum == 0 and sum_emp == 0:
                    results.append(arr.copy())
                return results
            if arr[index]==1:
                return possible_values_line(arr, sum - (index + 1), sum_emp, index + 1)
            elif arr[index]==2:
                return possible_values_line(arr, sum, sum_emp - (index + 1), index + 1)
            arr[index] = 1
            results.extend(possible_values_line(arr, sum - (index + 1), sum_emp, index + 1))
            arr[index] = 2
            results.extend(possible_values_line(arr, sum, sum_emp - (index + 1), index + 1))
            arr[index] = 0
            return results
        
        def common_values_line(arr, sum):
            possible_lines = possible_values_line(arr.copy(), sum)
            # print ("Possible lines:", possible_lines, "for sum", sum, "and arr", arr)
            if not possible_lines:
                return None
            common = [possible_lines[0][i] for i in range(len(arr))]
            for line in possible_lines[1:]:
                for i in range(len(arr)):
                    if common[i] != line[i]:
                        common[i] = 0
            return common
        def submit_common():
            updated = 0
            # Check rows
            for i in range(height):
                common = common_values_line(board[i], row_sums[i])
                if common is not None:
                    for j in range(width):
                        if common[j] != 0 and board[i][j] != common[j]:
                            board[i][j] = common[j]
                            updated += 1
            # Check columns
            for j in range(width):
                col = [board[i][j] for i in range(height)]
                common = common_values_line(col, col_sums[j])
                if common is not None:
                    for i in range(height):
                        if common[i] != 0 and board[i][j] != common[i]:
                            board[i][j] = common[i]
                            updated += 1
            return updated
        s = submit_common()
        while s > 0:
             print(s)
             s = submit_common()
        

        def is_valid():
            # Check row sums
            for i in range(height):
                if sum((j + 1) * (board[i][j]==1) for j in range(width)) != row_sums[i]:
                    return False
            # Check column sums
            for j in range(width):
                if sum((i + 1) * (board[i][j]==1) for i in range(height)) != col_sums[j]:
                    return False
            return True

        def solve_kakurasu(cell_idx=0):
            if cell_idx >= height * width:
                return is_valid()
            i, j = divmod(cell_idx, width)
            for value in [1, 2]:
                board[i][j] = value
                if solve_kakurasu(cell_idx + 1):
                    return True
                board[i][j] = 0
            return False

        # solve_kakurasu() ## surprisingly not needed, if needed uncomment this
        print(board)
        return board
