from dataclasses import dataclass
from typing import Literal

import tyro

from congkak.congkak_core import (
    BoardState,
    RuleConfig,
    apply_move,
    get_final_scores,
    get_legal_moves,
    get_winner,
    is_terminal,
)
from congkak.solver.minimax import MinimaxSolver


@dataclass
class Config:
    """Congkak game configuration."""

    # game rules
    simultaneous_start: bool = False
    """First move is simultaneous (both players pick at once)."""

    capture: bool = True
    """Landing in own empty pit captures opposite."""

    forfeit: bool = True
    """Landing in opponent empty pit forfeits seed."""

    burnt_holes: bool = False
    """Multi-round play with burnt holes (not yet implemented)."""

    # players
    p0: Literal["human", "ai", "random"] = "human"
    """Player 0 type."""

    p1: Literal["human", "ai", "random"] = "ai"
    """Player 1 type."""

    ai_depth: int = 8
    """Search depth for AI players."""

    # display
    gui: bool = True
    """Use pygame GUI instead of terminal."""

    animation_delay: int = 0
    """Delay in milliseconds after each move (0 = instant)."""


def print_board(state: BoardState) -> None:
    """Print the board to terminal."""
    pits = state.pits

    # player 1's pits (top row, displayed right to left)
    p1_pits = "  ".join(f"{pits[i]:2}" for i in range(13, 6, -1))
    # player 0's pits (bottom row, displayed left to right)
    p0_pits = "  ".join(f"{pits[i]:2}" for i in range(7))

    print()
    print(f"     P1 pits: {p1_pits}")
    print(f"  [{pits[15]:2}]" + " " * 30 + f"[{pits[14]:2}]")
    print(f"     P0 pits: {p0_pits}")
    print("  P1 store                          P0 store")
    print()


def get_human_move(state: BoardState, legal_moves: list[int]) -> int:
    """Get move from human player via terminal input."""
    player = state.current_player
    pit_start, _ = BoardState.player_pit_range(player)

    # display moves as 1-indexed for user
    display_moves = [m - pit_start + 1 for m in legal_moves]

    while True:
        try:
            prompt = f"Player {player}, choose pit {display_moves}: "
            choice = int(input(prompt))
            pit_idx = choice - 1 + pit_start
            if pit_idx in legal_moves:
                return pit_idx
            print(f"Invalid choice. Pick from {display_moves}")
        except ValueError:
            print("Enter a number.")
        except EOFError:
            raise SystemExit from None


def get_random_move(legal_moves: list[int]) -> int:
    """Pick a random legal move."""
    import random

    return random.choice(legal_moves)


def run_terminal_game(config: Config, rules: RuleConfig) -> None:
    """Run the game in terminal mode."""
    state = BoardState.initial()
    solver = MinimaxSolver(rules, max_depth=config.ai_depth)
    player_types = [config.p0, config.p1]

    print("Congkak - Terminal Mode")
    print("=" * 40)
    print(f"Rules: capture={config.capture}, forfeit={config.forfeit}")
    print(f"Players: P0={config.p0}, P1={config.p1}")
    print()

    while not is_terminal(state):
        print_board(state)
        legal_moves = get_legal_moves(state)
        current_player = state.current_player
        player_type = player_types[current_player]

        print(f"Player {current_player}'s turn ({player_type})")

        if player_type == "human":
            move = get_human_move(state, legal_moves)
        elif player_type == "ai":
            print("AI thinking...")
            move = solver.get_best_move(state)
            assert move is not None
            pit_start, _ = BoardState.player_pit_range(current_player)
            print(f"AI plays pit {move - pit_start + 1}")
        else:  # random
            move = get_random_move(legal_moves)
            pit_start, _ = BoardState.player_pit_range(current_player)
            print(f"Random plays pit {move - pit_start + 1}")

        result = apply_move(state, move, rules)
        state = result.state

        if result.extra_turn:
            print("Extra turn!")
        if result.captured > 0:
            print(f"Captured {result.captured} seeds!")

    # game over
    print_board(state)
    print("=" * 40)
    print("GAME OVER")

    p0_score, p1_score = get_final_scores(state)
    print(f"Final Score: P0 {p0_score} - {p1_score} P1")

    winner = get_winner(state)
    if winner == 0:
        print("Player 0 wins!")
    elif winner == 1:
        print("Player 1 wins!")
    else:
        print("Draw!")


def main(config: Config | None = None) -> None:
    """Main entry point."""
    if config is None:
        config = tyro.cli(Config)

    rules = RuleConfig(
        simultaneous_start=config.simultaneous_start,
        capture_enabled=config.capture,
        forfeit_enabled=config.forfeit,
        burnt_holes_enabled=config.burnt_holes,
    )

    if config.gui:
        from congkak.gui.app import run_gui

        run_gui(
            p0_type=config.p0,
            p1_type=config.p1,
            ai_depth=config.ai_depth,
            rules=rules,
            animation_delay=config.animation_delay,
        )
    else:
        run_terminal_game(config, rules)


if __name__ == "__main__":
    main()
