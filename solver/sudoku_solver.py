from .solver import BaseSolver
from itertools import combinations


class SudokuSolver(BaseSolver):
    """Solver for Sudoku puzzles (regular and irregular/jigsaw variants).
    
    Uses constraint propagation and backtracking with advanced techniques like
    naked subsets and box/row/column elimination.
    """
    
    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        """Initialize the Sudoku solver.
        
        Args:
            info: Dictionary containing puzzle information including:
                - table: Initial board state (2D list)
                - subtable_type: "regular" or "irregular"
                - subtable_height, subtable_width: For regular sudoku
                - boxes, boxes_table: For irregular/jigsaw sudoku
            show_progress: If True, show progress updates during solving.
            partial_solution_callback: Optional callback to display partial solution.
            progress_interval: Interval in seconds for progress updates (default: 10.0).
            partial_interval: Interval in seconds for partial solution display (default: 100.0).
        """
        super().__init__(info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                        progress_interval=progress_interval, partial_interval=partial_interval)
        self.board = info.get("table", [[0 for _ in range(self.width)] 
                                        for _ in range(self.height)])
        self.possible_values_cache = {}
        self.cells_to_fill = []
        
        # Find all empty cells
        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 0:
                    self.cells_to_fill.append((i, j))
        
        self.subtable_type = info["subtable_type"]
        if self.subtable_type == "regular":
            self.subtable_height = self.info["subtable_height"]
            self.subtable_width = self.info["subtable_width"]
        elif self.subtable_type == "irregular":
            self.boxes = self.info["boxes"]  # dict of indices for each box
            self.boxes_table = self.info["boxes_table"]  # box ID for each cell
        
        # Maximum size for naked subset detection
        self.Kmax = max(self.height // 2, 2)
        self.trim_is_overkill = True 
        

    def is_valid(self, num, row, col):
        """Check if placing a number at the given position is valid.
        
        Args:
            num: Number to place (1 to width)
            row: Row index
            col: Column index
        
        Returns:
            True if the placement is valid, False otherwise.
        """
        # Check row
        for x in range(self.width):
            if self.board[row][x] == num:
                return False
        
        # Check column
        for x in range(self.height):
            if self.board[x][col] == num:
                return False
        
        # Check subtable/box
        if self.subtable_type == "regular":
            start_row = self.subtable_height * (row // self.subtable_height)
            start_col = self.subtable_width * (col // self.subtable_width)
            for i in range(self.subtable_height):
                for j in range(self.subtable_width):
                    if self.board[start_row + i][start_col + j] == num:
                        return False
        elif self.subtable_type == "irregular":
            box_id = self.boxes_table[row][col]
            for r, c in self.boxes[box_id]:
                if self.board[r][c] == num:
                    return False
        
        return True
    
    def possible_values(self, row, col):
        """Calculate possible values for a cell based on current board state.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            List of possible values for the cell.
        """
        values = set(range(1, self.width + 1))
        
        # Remove values already in row
        for x in range(self.width):
            if self.board[row][x] in values:
                values.remove(self.board[row][x])
        
        # Remove values already in column
        for x in range(self.height):
            if self.board[x][col] in values:
                values.remove(self.board[x][col])
        
        # Remove values already in subtable/box
        if self.subtable_type == "regular":
            start_row = self.subtable_height * (row // self.subtable_height)
            start_col = self.subtable_width * (col // self.subtable_width)
            for r in range(self.subtable_height):
                for c in range(self.subtable_width):
                    if self.board[start_row + r][start_col + c] in values:
                        values.remove(self.board[start_row + r][start_col + c])
        elif self.subtable_type == "irregular":
            box_id = self.boxes_table[row][col]
            for r, c in self.boxes[box_id]:
                if self.board[r][c] in values:
                    values.remove(self.board[r][c])

        self.possible_values_cache[(row, col)] = values
        return list(values)
    
    def possible_values_extended(self, row, col):
        """Get cached possible values for a cell (after trimming).
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            List of possible values from cache.
        """
        return list(self.possible_values_cache[(row, col)])
    
    def regular_table_trim(self):
        """Apply constraint propagation for regular sudoku boxes.
        
        Uses hidden singles and pointing pairs/triples to eliminate candidates.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = 0
        for r0 in range(0, self.height, self.subtable_height):
            for c0 in range(0, self.width, self.subtable_width):
                # Collect candidates in this box
                num_positions = {n: [] for n in range(1, self.width + 1)}

                for r in range(r0, r0 + self.subtable_height):
                    for c in range(c0, c0 + self.subtable_width):
                        if (r, c) in self.possible_values_cache:
                            for n in self.possible_values_cache[(r, c)]:
                                num_positions[n].append((r, c))

                # Analyze each number
                for n, cells in num_positions.items():
                    if len(cells) == 0:
                        continue
                    
                    # Hidden single: only one position for this number
                    if len(cells) == 1:
                        r, c = cells[0]
                        if (r, c) in self.possible_values_cache and n in self.possible_values_cache[(r, c)]:
                            updated += len(self.possible_values_cache[(r, c)]) - 1
                            self.possible_values_cache[(r, c)] = {n}
                        continue

                    rows = {r for r, _ in cells}
                    cols = {c for _, c in cells}

                    # Pointing pairs/triples: if all candidates are in one row
                    if len(rows) == 1:
                        row = rows.pop()
                        for c in range(self.width):
                            if not (c0 <= c < c0 + self.subtable_width):
                                if (row, c) in self.possible_values_cache and n in self.possible_values_cache[(row, c)]:
                                    self.possible_values_cache[(row, c)].remove(n)
                                    updated += 1

                    # Pointing pairs/triples: if all candidates are in one column
                    if len(cols) == 1:
                        col = cols.pop()
                        for r in range(self.height):
                            if not (r0 <= r < r0 + self.subtable_height):
                                if (r, col) in self.possible_values_cache and n in self.possible_values_cache[(r, col)]:
                                    self.possible_values_cache[(r, col)].remove(n)
                                    updated += 1
        return updated
    def irregular_table_trim(self):
        """Apply constraint propagation for irregular/jigsaw sudoku boxes.
        
        Similar to regular_table_trim but works with irregular box shapes.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = 0
        for box_cells in self.boxes:
            num_positions = {n: [] for n in range(1, self.width + 1)}

            for (r, c) in box_cells:
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))

            for n, cells in num_positions.items():
                # Hidden single
                if len(cells) == 1:
                    r, c = cells[0]
                    if self.possible_values_cache[(r, c)] != {n}:
                        updated += len(self.possible_values_cache[(r, c)]) - 1
                        self.possible_values_cache[(r, c)] = {n}

                rows = {r for r, _ in cells}
                cols = {c for _, c in cells}

                # Pointing pairs: all candidates in one row
                if len(rows) == 1:
                    row = rows.pop()
                    for c in range(self.width):
                        if (row, c) not in box_cells and (row, c) in self.possible_values_cache:
                            if n in self.possible_values_cache[(row, c)]:
                                self.possible_values_cache[(row, c)].remove(n)
                                updated += 1

                # Pointing pairs: all candidates in one column
                if len(cols) == 1:
                    col = cols.pop()
                    for r in range(self.height):
                        if (r, col) not in box_cells and (r, col) in self.possible_values_cache:
                            if n in self.possible_values_cache[(r, col)]:
                                self.possible_values_cache[(r, col)].remove(n)
                                updated += 1
        return updated
    
    def trim_naked_subsets(self):
        """Apply naked subset elimination (pairs, triples, etc.).
        
        If k cells in a unit contain only k values total, those values
        can be removed from other cells in the same unit.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = 0
        k_max = self.Kmax
        
        # Apply to rows
        for r in range(self.height):
            unit_cells = [
                (r, c) for c in range(self.width)
                if (r, c) in self.possible_values_cache
            ]

            for k in range(1, min(k_max, len(unit_cells)) + 1):
                candidates = [
                    cell for cell in unit_cells
                    if 1 <= len(self.possible_values_cache[cell]) <= k
                ]

                for combo in combinations(candidates, k):
                    union_vals = set().union(
                        *(self.possible_values_cache[cell] for cell in combo)
                    )
                    if len(union_vals) == k:
                        for cell in unit_cells:
                            if cell not in combo:
                                before = set(self.possible_values_cache[cell])
                                after = before - union_vals
                                if after != before:
                                    self.possible_values_cache[cell] = after
                                    updated += 1

        # Apply to columns
        for c in range(self.width):
            unit_cells = [
                (r, c) for r in range(self.height)
                if (r, c) in self.possible_values_cache
            ]

            for k in range(1, min(k_max, len(unit_cells)) + 1):
                candidates = [
                    cell for cell in unit_cells
                    if 1 <= len(self.possible_values_cache[cell]) <= k
                ]

                for combo in combinations(candidates, k):
                    union_vals = set().union(
                        *(self.possible_values_cache[cell] for cell in combo)
                    )
                    if len(union_vals) == k:
                        for cell in unit_cells:
                            if cell not in combo:
                                before = set(self.possible_values_cache[cell])
                                after = before - union_vals
                                if after != before:
                                    self.possible_values_cache[cell] = after
                                    updated += 1
        return updated
    def trim_singles(self):
        """Apply hidden single elimination.
        
        If a number can only appear in one cell of a row/column,
        that cell must contain that number.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = 0
        
        # Check rows
        for r in range(self.height):
            num_positions = {n: [] for n in range(1, self.width + 1)}
            for c in range(self.width):
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))
            for num, positions in num_positions.items():
                if len(positions) == 1:
                    cell = positions[0]
                    if self.possible_values_cache[cell] != {num}:
                        self.possible_values_cache[cell] = {num}
                        updated += 1
        
        # Check columns
        for c in range(self.width):
            num_positions = {n: [] for n in range(1, self.width + 1)}
            for r in range(self.height):
                if (r, c) in self.possible_values_cache:
                    for n in self.possible_values_cache[(r, c)]:
                        num_positions[n].append((r, c))
            for num, positions in num_positions.items():
                if len(positions) == 1:
                    cell = positions[0]
                    if self.possible_values_cache[cell] != {num}:
                        self.possible_values_cache[cell] = {num}
                        updated += 1
        return updated

    def possible_values_trim(self):
        """Apply all constraint propagation techniques to eliminate candidates.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = 0
        if not self.trim_is_overkill:
            updated += self.trim_singles()
            updated += self.trim_naked_subsets()
        
        if self.subtable_type == "regular":
            updated += self.regular_table_trim()
        elif self.subtable_type == "irregular":
            updated += self.irregular_table_trim()
        
        return updated
    
    def solve(self):
        """Solve the sudoku puzzle using backtracking with constraint propagation.
        
        Returns:
            2D list representing the solved puzzle board.
        """
        self._start_progress_tracking()
        total_cells = len(self.cells_to_fill)
        backtrack_count = [0]  # Use list to allow modification in nested function
        
        def solve_sudoku(cell_idx=0):
            """Recursive backtracking solver with constraint propagation.
            
            Args:
                cell_idx: Index of current cell to fill in cells_to_fill list
            
            Returns:
                True if puzzle is solved, False otherwise.
            """
            if cell_idx >= len(self.cells_to_fill):
                return True
            
            # Update progress
            cells_filled = sum(1 for i, j in self.cells_to_fill[:cell_idx] if self.board[i][j] != 0)
            self._update_progress(
                cell_idx=cell_idx,
                total_cells=total_cells,
                cells_filled=cells_filled,
                current_cell=self.cells_to_fill[cell_idx] if cell_idx < len(self.cells_to_fill) else None,
                backtrack_count=backtrack_count[0]
            )
            
            # Clear cache and recalculate possible values
            self.possible_values_cache.clear()
            sorted_cells = sorted(
                self.cells_to_fill[cell_idx:],
                key=lambda x: len(self.possible_values(x[0], x[1]))
            )
            self.cells_to_fill[cell_idx:] = sorted_cells
            
            # Apply constraint propagation
            while self.possible_values_trim():
                pass
            
            # Re-sort based on trimmed possible values
            sorted_cells = sorted(
                self.cells_to_fill[cell_idx:],
                key=lambda x: len(self.possible_values_extended(x[0], x[1]))
            )
            self.cells_to_fill[cell_idx:] = sorted_cells
            
            i, j = self.cells_to_fill[cell_idx]
            if self.board[i][j] != 0:
                return solve_sudoku(cell_idx + 1)
            
            # Try each possible value
            pos_lst = list(self.possible_values_cache[(i, j)])
            for num in pos_lst:
                if self.is_valid(num, i, j):
                    self.board[i][j] = num
                    if solve_sudoku(cell_idx + 1):
                        return True
                    self.board[i][j] = 0  # Backtrack
                    backtrack_count[0] += 1
            
            return False

        try:
            solve_sudoku()
        finally:
            self._stop_progress_tracking()
        
        return self.board
    