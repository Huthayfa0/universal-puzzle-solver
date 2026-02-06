from .solver import BaseSolver


class KakurasuSolver(BaseSolver):
    """Solver for Kakurasu puzzles.
    
    Kakurasu is a puzzle where you fill cells to match row and column sums.
    Each cell's value is its position number (1-indexed) if filled, or 0 if empty.
    """
    
    def __init__(self, info, show_progress=True):
        """Initialize the Kakurasu solver.
        
        Args:
            info: Dictionary containing:
                - horizontal_borders: Target sums for each row
                - vertical_borders: Target sums for each column
                - height, width: Puzzle dimensions
            show_progress: If True, show progress updates during solving.
        """
        super().__init__(info, show_progress=show_progress)
        self.row_info = self.info["horizontal_borders"]
        self.col_info = self.info["vertical_borders"]
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def possible_values_line(self, arr, val, sum_emp=None, index=0):
        """Generate all possible line configurations that satisfy the sum constraint.
        
        Args:
            arr: Current line state (0=empty, 1=filled, 2=marked empty)
            val: Target sum for filled cells
            sum_emp: Sum of positions for empty cells (auto-calculated if None)
            index: Current position in the line
        
        Returns:
            List of valid line configurations.
        """
        if val < 0 or (sum_emp is not None and sum_emp < 0):
            return []
        
        if sum_emp is None:
            sum_emp = len(arr) * (len(arr) + 1) // 2 - val
        
        results = []
        if index >= len(arr):
            if val == 0 and sum_emp == 0:
                results.append(arr.copy())
            return results
        
        # Cell already filled
        if arr[index] == 1:
            return self.possible_values_line(arr, val - (index + 1), sum_emp, index + 1)
        # Cell already marked empty
        elif arr[index] == 2:
            return self.possible_values_line(arr, val, sum_emp - (index + 1), index + 1)
        
        # Try filling the cell
        arr[index] = 1
        results.extend(self.possible_values_line(arr, val - (index + 1), sum_emp, index + 1))
        
        # Try marking empty
        arr[index] = 2
        results.extend(self.possible_values_line(arr, val, sum_emp - (index + 1), index + 1))
        
        arr[index] = 0
        return results
    
    def common_values_line(self, arr, val):
        """Find common values across all possible line configurations.
        
        Args:
            arr: Current line state
            val: Target sum
        
        Returns:
            List where each position has the common value (0 if inconsistent),
            or None if no valid configurations exist.
        """
        possible_lines = self.possible_values_line(arr.copy(), val)
        if not possible_lines:
            return None
        
        common = [possible_lines[0][i] for i in range(len(arr))]
        for line in possible_lines[1:]:
            for i in range(len(arr)):
                if common[i] != line[i]:
                    common[i] = 0
        return common

    def submit_common(self):
        """Apply common value deduction to all rows and columns.
        
        Returns:
            Number of cells updated.
        """
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
        """Check if the current board state satisfies all constraints.
        
        Returns:
            True if valid, False otherwise.
        """
        # Check row sums
        for i in range(self.height):
            row_sum = sum((j + 1) * (self.board[i][j] == 1) for j in range(self.width))
            if row_sum != self.row_info[i]:
                return False
        
        # Check column sums
        for j in range(self.width):
            col_sum = sum((i + 1) * (self.board[i][j] == 1) for i in range(self.height))
            if col_sum != self.col_info[j]:
                return False
        return True

    def solve_puzzle(self, cell_idx=0):
        """Backtracking solver (typically not needed after constraint propagation).
        
        Args:
            cell_idx: Current cell index (row-major order)
        
        Returns:
            True if puzzle is solved, False otherwise.
        """
        if cell_idx >= self.height * self.width:
            return self.is_valid()
        
        i, j = divmod(cell_idx, self.width)
        if self.board[i][j] == 0:
            return self.solve_puzzle(cell_idx + 1)
        
        for value in [1, 2]:
            self.board[i][j] = value
            if self.solve_puzzle(cell_idx + 1):
                return True
            self.board[i][j] = 0
        return False
    
    def solve(self):
        """Solve the Kakurasu puzzle using constraint propagation.
        
        Returns:
            2D list representing the solved puzzle board.
        """
        s = self.submit_common()
        while s > 0:
            s = self.submit_common()
        # Note: solve_puzzle() is typically not needed after constraint propagation
        return self.board
