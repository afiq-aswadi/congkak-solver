from collections.abc import Callable
from math import inf

from congkak.congkak_core import (
    BoardState,
    RuleConfig,
    apply_move,
    get_final_scores,
    get_legal_moves,
    is_terminal,
)
from congkak.solver.evaluation import weighted_eval
from congkak.solver.transposition import TranspositionTable, TTFlag


class MinimaxSolver:
    """Minimax solver with alpha-beta pruning and transposition table."""

    def __init__(
        self,
        rules: RuleConfig,
        max_depth: int = 10,
        eval_fn: Callable[[BoardState, int], float] | None = None,
        use_tt: bool = True,
    ):
        self.rules = rules
        self.max_depth = max_depth
        self.eval_fn = eval_fn or weighted_eval
        self.tt = TranspositionTable() if use_tt else None
        self.nodes_searched = 0

    def get_best_move(self, state: BoardState) -> int | None:
        """Find the best move for the current player."""
        self.nodes_searched = 0
        _, move = self._alphabeta(state, self.max_depth, -inf, inf, state.current_player)
        return move

    def _terminal_value(self, state: BoardState, maximizing_player: int) -> float:
        """Return terminal state value (large positive for win, negative for loss)."""
        p0_score, p1_score = get_final_scores(state)
        diff = p0_score - p1_score if maximizing_player == 0 else p1_score - p0_score

        # scale terminal values to be larger than any evaluation
        if diff > 0:
            return 1000.0 + diff
        elif diff < 0:
            return -1000.0 + diff
        return 0.0

    def _alphabeta(
        self,
        state: BoardState,
        depth: int,
        alpha: float,
        beta: float,
        maximizing_player: int,
    ) -> tuple[float, int | None]:
        """Alpha-beta search.

        Returns (value, best_move).
        """
        self.nodes_searched += 1
        state_hash = hash(state)

        # terminal check
        if is_terminal(state):
            return self._terminal_value(state, maximizing_player), None

        # depth limit
        if depth == 0:
            return self.eval_fn(state, maximizing_player), None

        # transposition table lookup
        if self.tt is not None:
            tt_result = self.tt.lookup(state_hash, depth, alpha, beta)
            if tt_result is not None:
                value, is_exact = tt_result
                if is_exact:
                    return value, self.tt.get_best_move(state_hash)
                return value, self.tt.get_best_move(state_hash)

        moves = get_legal_moves(state)
        assert moves, f"no legal moves but not terminal: {state}"

        # move ordering: try TT best move first
        if self.tt is not None:
            tt_move = self.tt.get_best_move(state_hash)
            if tt_move is not None and tt_move in moves:
                moves.remove(tt_move)
                moves.insert(0, tt_move)

        best_move: int | None = moves[0]
        is_maximizing = state.current_player == maximizing_player

        if is_maximizing:
            value = -inf
            for move in moves:
                result = apply_move(state, move, self.rules)
                child_value, _ = self._alphabeta(
                    result.state, depth - 1, alpha, beta, maximizing_player
                )
                if child_value > value:
                    value = child_value
                    best_move = move
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            flag = TTFlag.LOWER_BOUND if value >= beta else TTFlag.EXACT
        else:
            value = inf
            for move in moves:
                result = apply_move(state, move, self.rules)
                child_value, _ = self._alphabeta(
                    result.state, depth - 1, alpha, beta, maximizing_player
                )
                if child_value < value:
                    value = child_value
                    best_move = move
                beta = min(beta, value)
                if alpha >= beta:
                    break
            flag = TTFlag.UPPER_BOUND if value <= alpha else TTFlag.EXACT

        # store in transposition table
        if self.tt is not None:
            self.tt.store(state_hash, value, depth, flag, best_move)

        return value, best_move

    def clear_tt(self) -> None:
        """Clear the transposition table."""
        if self.tt is not None:
            self.tt.clear()
