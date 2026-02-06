class BaseSolver:
    """Base class for all puzzle solvers.
    
    Provides common functionality and interface for solving different types of puzzles.
    Subclasses must implement the solve() method.
    """
    
    def __init__(self, info=None):
        """Initialize the solver with puzzle information.
        
        Args:
            info: Dictionary containing puzzle metadata (height, width, type, etc.)
                  If None, an empty dict is used.
        """
        self.info = info if info is not None else {}
        self.height = self.info["height"]
        self.width = self.info["width"]
    
    def solve(self):
        """Solve the puzzle and return the solution.
        
        Returns:
            The solved puzzle board/grid.
        
        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

