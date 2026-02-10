"""Base solver for chess capture puzzles.

Shared logic for puzzles where:
- Pieces move as standard chess pieces.
- Only capture moves are allowed.
- Goal is to end up with one piece on the board.

Subclasses customize: king capture allowed, move limits, turn order (single color vs white/black).
"""

from .solver import BaseSolver


# Piece codes: uppercase = white / "friendly", lowercase = black (for two-sided)
# K/k=King, Q/q=Queen, R/r=Rook, B/b=Bishop, N/n=Knight, P/p=Pawn
PIECE_CHARS = "KQRBNPkqrbnp"
# Map parser integers to piece chars. Parser often stores 0 as 2, so 0 and 2 = empty.
# 1=K, 3=Q, 4=R, 5=B, 6=N, 7=P (white); 8=k, 9=q, 10=r, 11=b, 12=n, 13=p (black).
INT_TO_PIECE = {
    1: "K", 3: "Q", 4: "R", 5: "B", 6: "N", 7: "P",
    8: "k", 9: "q", 10: "r", 11: "b", 12: "n", 13: "p",
}
PIECE_TO_INT = {"K": 1, "Q": 3, "R": 4, "B": 5, "N": 6, "P": 7, "k": 8, "q": 9, "r": 10, "b": 11, "n": 12, "p": 13}

# Empty cell in parser: 0 is often stored as 2
EMPTY_VALS = (0, 2, None)


def _parse_cell(cell):
    """Convert a table cell to piece char or None (empty)."""
    if cell in EMPTY_VALS or cell == "":
        return None
    if isinstance(cell, str) and len(cell) == 1 and cell in PIECE_CHARS:
        return cell
    if isinstance(cell, int) and cell in INT_TO_PIECE:
        return INT_TO_PIECE[cell]
    return None


def _board_from_table(table, height, width):
    """Build board (list of lists of piece char or None) from parser table."""
    if not table or not table[0]:
        return [[None] * width for _ in range(height)]
    board = []
    for r in range(height):
        row = []
        for c in range(width):
            val = table[r][c] if r < len(table) and c < len(table[r]) else 0
            row.append(_parse_cell(val))
        board.append(row)
    return board


def _copy_board(board):
    """Deep copy of board."""
    return [row[:] for row in board]


def _piece_at(board, r, c, height, width):
    if 0 <= r < height and 0 <= c < width:
        return board[r][c]
    return None


def _is_white(piece):
    return piece is not None and piece.isupper()


def _is_black(piece):
    return piece is not None and piece.lower() == piece and piece in PIECE_CHARS


def _is_king(piece):
    return piece is not None and piece.upper() == "K"


# Offsets for sliding and king
_ORTH = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_KNIGHT = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1),
]


def _slide_captures(board, height, width, r, c, directions):
    """Yield (nr, nc) for each square that can be captured by sliding in given directions."""
    piece = board[r][c]
    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        while 0 <= nr < height and 0 <= nc < width:
            target = board[nr][nc]
            if target is not None:
                yield (nr, nc)
                break
            nr, nc = nr + dr, nc + dc


def _single_captures(board, height, width, r, c, offsets):
    """Yield (nr, nc) for each capture one step in given directions."""
    for dr, dc in offsets:
        nr, nc = r + dr, c + dc
        if 0 <= nr < height and 0 <= nc < width and board[nr][nc] is not None:
            yield (nr, nc)


def _pawn_captures_white(board, height, width, r, c):
    """White pawns move toward higher row (row increases downward)."""
    for dc in (-1, 1):
        nr, nc = r + 1, c + dc
        if 0 <= nr < height and 0 <= nc < width and board[nr][nc] is not None:
            yield (nr, nc)


def _pawn_captures_black(board, height, width, r, c):
    """Black pawns move toward lower row."""
    for dc in (-1, 1):
        nr, nc = r - 1, c + dc
        if 0 <= nr < height and 0 <= nc < width and board[nr][nc] is not None:
            yield (nr, nc)


def get_capture_squares(board, height, width, r, c, pawn_forward_down=True):
    """Yield (nr, nc) for every square the piece at (r,c) can capture on.

    For single-color puzzles (Solo/Ranger), pass pawn_forward_down=True so pawns move toward higher row.
    """
    piece = board[r][c]
    if piece is None:
        return
    p = piece.upper()
    if p == "K":
        yield from _single_captures(board, height, width, r, c, _ORTH + _DIAG)
    elif p == "Q":
        yield from _slide_captures(board, height, width, r, c, _ORTH + _DIAG)
    elif p == "R":
        yield from _slide_captures(board, height, width, r, c, _ORTH)
    elif p == "B":
        yield from _slide_captures(board, height, width, r, c, _DIAG)
    elif p == "N":
        yield from _single_captures(board, height, width, r, c, _KNIGHT)
    elif p == "P":
        if _is_white(piece) or pawn_forward_down:
            yield from _pawn_captures_white(board, height, width, r, c)
        else:
            yield from _pawn_captures_black(board, height, width, r, c)


def apply_capture(board, fr, fc, tr, tc):
    """Apply capture: move piece from (fr,fc) to (tr,tc), remove target. Modifies board in place."""
    board[tr][tc] = board[fr][fc]
    board[fr][fc] = None


def count_pieces(board, height, width):
    """Return number of pieces on the board."""
    return sum(1 for r in range(height) for c in range(width) if board[r][c] is not None)


def list_pieces(board, height, width):
    """Yield (r, c, piece) for each piece."""
    for r in range(height):
        for c in range(width):
            p = board[r][c]
            if p is not None:
                yield (r, c, p)


class ChessCaptureBaseSolver(BaseSolver):
    """Base solver for capture-only chess puzzles.

    Subclasses must override:
    - is_goal(state) -> bool
    - get_valid_moves(state) -> list of (fr, fc, tr, tc)
    - apply_move(state, move) -> new state
    - state_to_key(state) -> hashable (for visited set)
    - initial_state() -> state
    """

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        table = info.get("table", [])
        self.height = info.get("height", 8)
        self.width = info.get("width", 8)
        self.board = _board_from_table(table, self.height, self.width)
        self.solution_moves = []

    def is_goal(self, state):
        """Return True if state is a winning configuration. Override in subclasses."""
        raise NotImplementedError

    def get_valid_moves(self, state):
        """Return list of (fr, fc, tr, tc) capture moves. Override in subclasses."""
        raise NotImplementedError

    def apply_move(self, state, move):
        """Return new state after move. Override in subclasses."""
        raise NotImplementedError

    def state_to_key(self, state):
        """Return hashable key for state. Override in subclasses."""
        raise NotImplementedError

    def initial_state(self):
        """Return initial state. Override in subclasses."""
        raise NotImplementedError

    def solve(self):
        """Search for a sequence of captures leading to goal. Returns final board or None.
        Uses iterative DFS with explicit stack to avoid recursion depth limits."""
        start = self.initial_state()
        visited = {self.state_to_key(start)}
        stack = [(start, [])]  # (state, path_from_start)

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            while stack:
                state, path = stack.pop()
                if self.is_goal(state):
                    self.solution_moves = path
                    return self._state_to_board(state)
                moves = self.get_valid_moves(state)
                if self.show_progress and self.progress_tracker and len(visited) % 500 == 0:
                    self._update_progress(call_count=len(visited), backtrack_count=len(stack))
                for move in moves:
                    new_state = self.apply_move(state, move)
                    key = self.state_to_key(new_state)
                    if key not in visited:
                        visited.add(key)
                        stack.append((new_state, path + [move]))
            return None
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

    def _state_to_board(self, state):
        """Extract board from state (state may be (board, ...) or just board)."""
        return state[0] if isinstance(state, (list, tuple)) and len(state) > 0 else state

    def _final_board_from_moves(self, initial_state, moves):
        """Apply moves to initial state and return final board."""
        state = initial_state
        for move in moves:
            state = self.apply_move(state, move)
        return self._state_to_board(state)

    def _board_to_table(self, board):
        """Convert board (piece chars / None) to table format (ints, 0 = empty)."""
        out = []
        for r in range(len(board)):
            row = []
            for c in range(len(board[r])):
                p = board[r][c]
                if p is None:
                    row.append(0)
                else:
                    row.append(PIECE_TO_INT.get(p, 0))
            out.append(row)
        return out
