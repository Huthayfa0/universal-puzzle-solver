class BaseSolver:
    def __init__(self, info={}):
        self.info = info
        self.height=self.info["height"]
        self.width = self.info["width"]
    def solve(self):
        raise NotImplementedError("This method should be overridden by subclasses.")

