class BaseSolver:
    def __init__(self, info={}):
        self.info = info
    def solve(self):
        raise NotImplementedError("This method should be overridden by subclasses.")

