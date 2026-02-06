import threading
import time


class ProgressTracker:
    """Tracks and reports solving progress at regular intervals."""
    
    def __init__(self, interval=10.0):
        """Initialize the progress tracker.
        
        Args:
            interval: Time interval in seconds between progress updates.
        """
        self.interval = interval
        self.start_time = None
        self.last_update_time = None
        self.progress_info = {}
        self.timer_thread = None
        self.active = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start the progress tracking timer."""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.active = True
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()
    
    def stop(self):
        """Stop the progress tracking timer."""
        self.active = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1.0)
    
    def update(self, **kwargs):
        """Update progress information.
        
        Args:
            **kwargs: Progress information to store (e.g., cell_idx, cells_filled, etc.)
        """
        with self.lock:
            self.progress_info.update(kwargs)
            self.last_update_time = time.time()
    
    def _timer_loop(self):
        """Timer loop that prints progress at regular intervals."""
        while self.active:
            time.sleep(self.interval)
            if not self.active:
                break
            
            with self.lock:
                elapsed = time.time() - self.start_time
                self._print_progress(elapsed)
    
    def _print_progress(self, elapsed):
        """Print current progress information.
        
        Args:
            elapsed: Time elapsed since start.
        """
        info_parts = []
        
        if "cell_idx" in self.progress_info:
            cell_idx = self.progress_info["cell_idx"]
            total_cells = self.progress_info.get("total_cells", "?")
            info_parts.append(f"Cell {cell_idx}/{total_cells}")
        
        if "cells_filled" in self.progress_info:
            filled = self.progress_info["cells_filled"]
            total = self.progress_info.get("total_cells", "?")
            percentage = (filled / total * 100) if isinstance(total, int) else "?"
            info_parts.append(f"{filled}/{total} cells filled ({percentage}%)" if isinstance(percentage, (int, float)) else f"{filled}/{total} cells filled")
        
        if "clue_idx" in self.progress_info:
            clue_idx = self.progress_info["clue_idx"]
            total_clues = self.progress_info.get("total_clues", "?")
            clue_type = self.progress_info.get("clue_type", "")
            info_parts.append(f"Processing {clue_type} clue {clue_idx}/{total_clues}")
        
        if "current_cell" in self.progress_info:
            cell = self.progress_info["current_cell"]
            info_parts.append(f"At cell ({cell[0]}, {cell[1]})")
        
        if "backtrack_count" in self.progress_info:
            info_parts.append(f"Backtracks: {self.progress_info['backtrack_count']}")
        
        progress_str = " | ".join(info_parts) if info_parts else "Solving..."
        print(f"[Progress @ {elapsed:.1f}s] {progress_str}")


class BaseSolver:
    """Base class for all puzzle solvers.
    
    Provides common functionality and interface for solving different types of puzzles.
    Subclasses must implement the solve() method.
    """
    
    def __init__(self, info=None, show_progress=True):
        """Initialize the solver with puzzle information.
        
        Args:
            info: Dictionary containing puzzle metadata (height, width, type, etc.)
                  If None, an empty dict is used.
            show_progress: If True, show progress updates every 10 seconds.
        """
        self.info = info if info is not None else {}
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.show_progress = show_progress
        self.progress_tracker = ProgressTracker(interval=10.0) if show_progress else None
    
    def solve(self):
        """Solve the puzzle and return the solution.
        
        Returns:
            The solved puzzle board/grid.
        
        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    def _start_progress_tracking(self):
        """Start progress tracking if enabled."""
        if self.progress_tracker:
            self.progress_tracker.start()
    
    def _stop_progress_tracking(self):
        """Stop progress tracking if enabled."""
        if self.progress_tracker:
            self.progress_tracker.stop()
    
    def _update_progress(self, **kwargs):
        """Update progress information if tracking is enabled.
        
        Args:
            **kwargs: Progress information to update.
        """
        if self.progress_tracker:
            self.progress_tracker.update(**kwargs)

