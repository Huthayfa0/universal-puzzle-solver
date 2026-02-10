"""Solo Chess puzzle solver.

Rules:
- Pieces move as standard chess pieces.
- Only capture moves are allowed.
- Each piece can move at most twice.
- You cannot capture the king.
- Goal: end up with exactly one piece on the board (the king).
"""

from .chess_capture_base import (
    ChessCaptureBaseSolver,
    _copy_board,
    get_capture_squares,
    apply_capture,
    count_pieces,
    _is_king,
    list_pieces,
)


class SoloChessSolver(ChessCaptureBaseSolver):
    """Solver for Solo Chess: capture-only, max 2 moves per piece, cannot capture king, goal = king alone."""

    def initial_state(self):
        board = _copy_board(self.board)
        move_counts = {}  # (r, c) -> number of times the piece at (r,c) has moved
        return (board, move_counts)

    def state_to_key(self, state):
        board, move_counts = state
        # Board as tuple of tuples; move_counts as sorted tuple of ((r,c), count)
        board_t = tuple(tuple(cell for cell in row) for row in board)
        mc_t = tuple(sorted((k, v) for k, v in move_counts.items()))
        return (board_t, mc_t)

    def is_goal(self, state):
        board, _ = state
        n = count_pieces(board, self.height, self.width)
        if n != 1:
            return False
        for r in range(self.height):
            for c in range(self.width):
                if board[r][c] is not None:
                    return _is_king(board[r][c])
        return False

    def get_valid_moves(self, state):
        board, move_counts = state
        moves = []
        for r in range(self.height):
            for c in range(self.width):
                piece = board[r][c]
                if piece is None:
                    continue
                if move_counts.get((r, c), 0) >= 2:
                    continue
                for tr, tc in get_capture_squares(board, self.height, self.width, r, c, pawn_forward_down=True):
                    target = board[tr][tc]
                    if target is not None and _is_king(target):
                        continue  # cannot capture the king
                    moves.append((r, c, tr, tc))
        return moves

    def apply_move(self, state, move):
        fr, fc, tr, tc = move
        board = _copy_board(state[0])
        move_counts = dict(state[1])
        count_before = move_counts.pop((fr, fc), 0)
        apply_capture(board, fr, fc, tr, tc)
        move_counts[(tr, tc)] = count_before + 1
        return (board, move_counts)

    def _state_to_board(self, state):
        return state[0]

    def solve(self):
        result = super().solve()
        if result is None:
            return None
        return self._board_to_table(result)
