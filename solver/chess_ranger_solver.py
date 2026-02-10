"""Chess Ranger puzzle solver.

Rules:
- Pieces move as standard chess pieces.
- Only capture moves are allowed.
- You are allowed to capture the king.
- Goal: end up with exactly one piece on the board (any piece).
"""

from .chess_capture_base import (
    ChessCaptureBaseSolver,
    _copy_board,
    get_capture_squares,
    apply_capture,
    count_pieces,
)


class ChessRangerSolver(ChessCaptureBaseSolver):
    """Solver for Chess Ranger: capture-only, king can be captured, goal = any single piece."""

    def initial_state(self):
        return _copy_board(self.board)

    def state_to_key(self, state):
        return tuple(tuple(cell for cell in row) for row in state)

    def is_goal(self, state):
        return count_pieces(state, self.height, self.width) == 1

    def get_valid_moves(self, state):
        moves = []
        for r in range(self.height):
            for c in range(self.width):
                if state[r][c] is None:
                    continue
                for tr, tc in get_capture_squares(state, self.height, self.width, r, c, pawn_forward_down=True):
                    if state[tr][tc] is not None:
                        moves.append((r, c, tr, tc))
        return moves

    def apply_move(self, state, move):
        fr, fc, tr, tc = move
        board = _copy_board(state)
        apply_capture(board, fr, fc, tr, tc)
        return board

    def _state_to_board(self, state):
        return state

    def solve(self):
        result = super().solve()
        if result is None:
            return None
        return self._board_to_table(result)
