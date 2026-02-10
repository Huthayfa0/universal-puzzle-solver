"""Chess Melee puzzle solver.

Rules:
- Pieces move as standard chess pieces.
- White moves first.
- Only capture moves are allowed.
- Goal: end up with exactly one piece on the board (any piece).
"""

from .chess_capture_base import (
    ChessCaptureBaseSolver,
    _copy_board,
    get_capture_squares,
    apply_capture,
    count_pieces,
    _is_white,
    _is_black,
)


class ChessMeleeSolver(ChessCaptureBaseSolver):
    """Solver for Chess Melee: white moves first, alternating turns, capture-only, goal = one piece."""

    def initial_state(self):
        board = _copy_board(self.board)
        return (board, "white")  # white moves first

    def state_to_key(self, state):
        board, side = state
        board_t = tuple(tuple(cell for cell in row) for row in board)
        return (board_t, side)

    def is_goal(self, state):
        board, _ = state
        return count_pieces(board, self.height, self.width) == 1

    def get_valid_moves(self, state):
        board, side = state
        moves = []
        is_white_turn = side == "white"
        for r in range(self.height):
            for c in range(self.width):
                piece = board[r][c]
                if piece is None:
                    continue
                if is_white_turn and not _is_white(piece):
                    continue
                if not is_white_turn and not _is_black(piece):
                    continue
                for tr, tc in get_capture_squares(board, self.height, self.width, r, c, pawn_forward_down=False):
                    target = board[tr][tc]
                    if target is None:
                        continue
                    # Can only capture opposite color
                    if is_white_turn and _is_black(target):
                        moves.append((r, c, tr, tc))
                    elif not is_white_turn and _is_white(target):
                        moves.append((r, c, tr, tc))
        return moves

    def apply_move(self, state, move):
        fr, fc, tr, tc = move
        board = _copy_board(state[0])
        side = state[1]
        apply_capture(board, fr, fc, tr, tc)
        next_side = "black" if side == "white" else "white"
        return (board, next_side)

    def _state_to_board(self, state):
        return state[0]

    def solve(self):
        result = super().solve()
        if result is None:
            return None
        return self._board_to_table(result)
