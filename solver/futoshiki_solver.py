from .sudoku_solver import SudokuSolver


class FutoshikiSolver(SudokuSolver):
    """Solver for Futoshiki puzzles (Sudoku with inequality constraints).
    
    Futoshiki adds greater-than/less-than constraints between adjacent cells.
    """
    
    def __init__(self, info, show_progress=True):
        """Initialize the Futoshiki solver.
        
        Args:
            info: Dictionary containing puzzle information including:
                - cell_info_table: Directions where current cell is greater
            show_progress: If True, show progress updates during solving.
        """
        super().__init__(info, show_progress=show_progress)
        self.trim_is_overkill = False
        self.adj_more = [[] for _ in range(self.height)]
        self.adj_less = [[] for _ in range(self.height)]
        
        for i in range(self.height):
            self.adj_more[i] = self.info["cell_info_table"][i]
            self.adj_less[i] = [[] for _ in range(self.width)]
        
        # Build reverse mapping: if (i,j) > (i+di, j+dj), then (i+di, j+dj) < (i,j)
        for i in range(self.height):
            for j in range(self.width):
                for direction in self.info["cell_info_table"][i][j]:
                    ni, nj = i + direction[0], j + direction[1]
                    if 0 <= ni < self.height and 0 <= nj < self.width:
                        self.adj_less[ni][nj].append((-direction[0], -direction[1])) 

    def is_valid(self, num, row, col):
        """Check if placing a number is valid, including Futoshiki constraints.
        
        Args:
            num: Number to place
            row: Row index
            col: Column index
        
        Returns:
            True if valid, False otherwise.
        """
        if not super().is_valid(num, row, col):
            return False
        
        # Check greater-than constraints
        for v in self.adj_more[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0 and neighbor_val >= num:
                return False
        
        # Check less-than constraints
        for v in self.adj_less[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0 and neighbor_val <= num:
                return False
        
        return True
    
    def possible_values(self, row, col):
        """Calculate possible values including Futoshiki constraints.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            List of possible values.
        """
        values = set(super().possible_values(row, col))
        
        # Filter by greater-than constraints
        for v in self.adj_more[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0:
                values = {c for c in values if neighbor_val < c}
        
        # Filter by less-than constraints
        for v in self.adj_less[row][col]:
            neighbor_val = self.board[row + v[0]][col + v[1]]
            if neighbor_val != 0:
                values = {c for c in values if neighbor_val > c}
        
        self.possible_values_cache[(row, col)] = values
        return list(values)
    
    def possible_values_trim(self):
        """Apply additional Futoshiki constraint propagation.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = super().possible_values_trim()
        
        # Apply inequality constraints to possibilities
        for i, j in self.possible_values_cache.keys():
            to_remove = set()
            if self.board[i][j] != 0:
                continue
            
            for n in self.possible_values_cache[(i, j)]:
                # Check greater-than constraints
                for v in self.adj_more[i][j]:
                    neighbor_pos = (i + v[0], j + v[1])
                    neighbor_vals = self.possible_values_cache.get(
                        neighbor_pos,
                        {self.board[i + v[0]][j + v[1]]} if self.board[i + v[0]][j + v[1]] != 0 else {1}
                    )
                    if not neighbor_vals:
                        neighbor_vals = {1}
                    if n <= min(neighbor_vals):
                        to_remove.add(n)
                
                # Check less-than constraints
                for v in self.adj_less[i][j]:
                    neighbor_pos = (i + v[0], j + v[1])
                    neighbor_vals = self.possible_values_cache.get(
                        neighbor_pos,
                        {self.board[i + v[0]][j + v[1]]} if self.board[i + v[0]][j + v[1]] != 0 else {self.height}
                    )
                    if not neighbor_vals:
                        neighbor_vals = {self.height}
                    if n >= max(neighbor_vals):
                        to_remove.add(n)
            
            updated += len(to_remove)
            self.possible_values_cache[(i, j)] -= to_remove
        
        return updated
    