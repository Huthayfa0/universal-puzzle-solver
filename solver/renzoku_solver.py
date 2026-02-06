from .sudoku_solver import SudokuSolver
from itertools import combinations


class RenzokuSolver(SudokuSolver):
    """Solver for Renzoku puzzles (Sudoku with adjacent number constraints).
    
    Renzoku adds constraints that adjacent cells must differ by exactly 1
    (marked with dots) or differ by more than 1 (no dot).
    """
    
    def __init__(self, info):
        """Initialize the Renzoku solver.
        
        Args:
            info: Dictionary containing puzzle information including:
                - cell_info_table: Adjacency constraints (directions with dots)
        """
        super().__init__(info)
        self.trim_is_overkill = False
        self.adj_dot = [[] for _ in range(self.height)]
        self.adj_ndot = [[] for _ in range(self.height)]
        self.all_dir = {(1, 0), (-1, 0), (0, 1), (0, -1)}
        
        for i in range(self.height):
            self.adj_dot[i] = self.info["cell_info_table"][i]
            self.adj_ndot[i] = [[] for _ in range(self.width)]
            for j in range(self.width):
                # Find directions without dots (must differ by >1)
                dot_dirs = set(self.info["cell_info_table"][i][j])
                no_dot_dirs = self.all_dir - dot_dirs
                self.adj_ndot[i][j] = [
                    a for a in no_dot_dirs
                    if 0 <= a[0] + i < self.height and 0 <= a[1] + j < self.width
                ]
            
    def is_valid(self, num, row, col):
        """Check if placing a number is valid, including Renzoku constraints.
        
        Args:
            num: Number to place
            row: Row index
            col: Column index
        
        Returns:
            True if valid, False otherwise.
        """
        if not super().is_valid(num, row, col):
            return False
        
        # Check dot constraints (must differ by exactly 1)
        for v in self.adj_dot[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0 and abs(neighbor_val - num) > 1:
                return False
        
        # Check no-dot constraints (must differ by more than 1)
        for v in self.adj_ndot[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0 and abs(neighbor_val - num) <= 1:
                return False
        
        return True

    def possible_values(self, row, col):
        """Calculate possible values including Renzoku constraints.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            List of possible values.
        """
        values = set(super().possible_values(row, col))
        
        # Filter by dot constraints
        for v in self.adj_dot[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0:
                values = {c for c in values if abs(neighbor_val - c) == 1}
        
        # Filter by no-dot constraints
        for v in self.adj_ndot[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0:
                values = {c for c in values if abs(neighbor_val - c) > 1}
        
        self.possible_values_cache[(row, col)] = values
        return list(values)

    def possible_values_trim(self):
        """Apply additional Renzoku constraint propagation.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = super().possible_values_trim()
        
        # Apply adjacency constraints to possibilities
        for i, j in self.possible_values_cache.keys():
            to_remove = set()
            if self.board[i][j] != 0:
                continue
            
            for n in self.possible_values_cache[(i, j)]:
                # Check dot constraints: must have neighbor with n±1
                for v in self.adj_dot[i][j]:
                    neighbor_pos = (i + v[0], j + v[1])
                    neighbor_vals = self.possible_values_cache.get(
                        neighbor_pos,
                        {self.board[i + v[0]][j + v[1]]}
                    )
                    if n + 1 not in neighbor_vals and n - 1 not in neighbor_vals:
                        to_remove.add(n)
                
                # Check no-dot constraints: neighbor cannot have n±1
                for v in self.adj_ndot[i][j]:
                    neighbor_pos = (i + v[0], j + v[1])
                    neighbor_vals = self.possible_values_cache.get(
                        neighbor_pos,
                        {self.board[i + v[0]][j + v[1]]}
                    )
                    if all(abs(x - n) <= 1 for x in neighbor_vals):
                        to_remove.add(n)
            
            updated += len(to_remove)
            self.possible_values_cache[(i, j)] -= to_remove
        
        return updated
    