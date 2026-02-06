from .sudoku_solver import SudokuSolver


class KillerSudokuSolver(SudokuSolver):
    """Solver for Killer Sudoku puzzles.
    
    Killer Sudoku adds cage constraints where cells in a cage must sum to a target,
    and optionally diagonal constraints (X variant).
    """
    
    def __init__(self, info, show_progress=True):
        """Initialize the Killer Sudoku solver.
        
        Args:
            info: Dictionary containing puzzle information including:
                - boxes/boxes_2: Cage definitions
                - boxes_table/boxes_table_2: Cage ID for each cell
                - table_2: Cage target sums
                - killer_x: Whether diagonal constraints apply
            show_progress: If True, show progress updates during solving.
        """
        super().__init__(info, show_progress=show_progress)
        self.trim_is_overkill = False
        
        # Use different box sets for regular vs irregular subtable types
        if self.subtable_type == "regular":
            self.sum_boxes = self.info["boxes"]
            self.sum_boxes_table = self.info["boxes_table"]
        else:
            self.sum_boxes = self.info["boxes_2"]
            self.sum_boxes_table = self.info["boxes_table_2"]
        
        # Extract cage target sums
        self.sums = [value for row in self.info["table_2"] for value in row if value != 0]
        self.killer_x = info.get("killer_x", False)  # True if diagonal constraints apply

  
    def _cage_info(self, row, col):
        """Get information about the cage containing the given cell.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            Tuple of (filled_values, empty_count, target_sum)
        """
        box = self.sum_boxes_table[row][col]
        cells = self.sum_boxes[box]
        target = self.sums[box]

        values = [
            self.board[r][c]
            for r, c in cells
            if self.board[r][c] != 0
        ]

        empty = sum(
            1 for r, c in cells
            if self.board[r][c] == 0
        )

        return values, empty, target

    def _cage_allows(self, num, row, col):
        """Check if placing a number satisfies cage sum constraints.
        
        Args:
            num: Number to place
            row: Row index
            col: Column index
        
        Returns:
            True if the placement is valid for the cage, False otherwise.
        """
        values, empty, target = self._cage_info(row, col)

        # Number already used in cage
        if num in values:
            return False

        s = sum(values) + num
        if s > target:
            return False

        # Last empty cell must equal target
        if empty == 1:
            return s == target

        # Check if target is achievable with remaining cells
        remaining = empty - 1
        unused = set(range(1, self.height + 1)) - set(values) - {num}

        min_possible = sum(sorted(unused)[:remaining])
        max_possible = sum(sorted(unused, reverse=True)[:remaining])

        return (s + min_possible <= target) and (s + max_possible >= target)

    def _x_allows(self, num, row, col):
        """Check if placing a number satisfies diagonal constraints (X variant).
        
        Args:
            num: Number to place
            row: Row index
            col: Column index
        
        Returns:
            True if valid, False otherwise.
        """
        if not self.killer_x:
            return True

        n = self.height

        # Check main diagonal (top-left to bottom-right)
        if row == col:
            for i in range(n):
                if self.board[i][i] == num:
                    return False

        # Check anti-diagonal (top-right to bottom-left)
        if row + col == n - 1:
            for i in range(n):
                if self.board[i][n - 1 - i] == num:
                    return False

        return True

    def is_valid(self, num, row, col):
        """Check if placing a number is valid, including Killer Sudoku constraints.
        
        Args:
            num: Number to place
            row: Row index
            col: Column index
        
        Returns:
            True if valid, False otherwise.
        """
        return (
            super().is_valid(num, row, col)
            and self._x_allows(num, row, col)
            and self._cage_allows(num, row, col)
        )

    def possible_values(self, row, col):
        """Calculate possible values including Killer Sudoku constraints.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            List of possible values.
        """
        values = set(super().possible_values(row, col))

        allowed = {
            n for n in values
            if self._x_allows(n, row, col)
            and self._cage_allows(n, row, col)
        }

        self.possible_values_cache[(row, col)] = allowed
        return list(allowed)

    def possible_values_trim(self):
        """Apply Killer Sudoku constraint propagation.
        
        Returns:
            Number of candidate eliminations made.
        """
        updated = super().possible_values_trim()

        for (i, j), vals in list(self.possible_values_cache.items()):
            if self.board[i][j] != 0:
                continue

            to_remove = {
                n for n in vals
                if not self._x_allows(n, i, j)
                or not self._cage_allows(n, i, j)
            }

            if to_remove:
                self.possible_values_cache[(i, j)] -= to_remove
                updated += len(to_remove)

        return updated
