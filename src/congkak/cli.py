from dataclasses import dataclass
from typing import Literal

import tyro

from congkak.congkak_core import (
    BoardState,
    LeaderSelection,
    RuleConfig,
    StartMode,
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
    start_mode: Literal["sequential", "independent", "leader_follower"] = "sequential"
    """Start mode: sequential, independent (both pick blind), or leader_follower."""

    leader_selection: Literal["random", "p0", "p1"] = "random"
    """How leader is selected in leader_follower mode: random, p0 (always p0), p1 (always p1)."""

    capture: bool = True
    """Landing in own empty pit captures opposite."""

    capture_requires_loop: bool = False
    """Capture only allowed after passing through own store."""

    forfeit: bool = True
    """Landing in opponent empty pit forfeits seed."""

    burnt_holes: bool = False
    """Multi-round play with burnt holes (not yet implemented)."""

    # players
    p0: Literal["human", "ai", "random"] = "human"
    """Player 0 type."""

    p1: Literal["human", "ai", "random"] = "ai"
    """Player 1 type."""

    p0_depth: int = 8
    """Search depth for P0 AI."""

    p1_depth: int = 8
    """Search depth for P1 AI."""

    # display
    gui: bool = True
    """Use pygame GUI instead of terminal."""

    animation_delay: int = 0
    """Delay in milliseconds after each move (0 = instant)."""

    # initial state
    p0_pits: str | None = None
    """P0's initial pit values as 7 comma-separated integers. Example: '7,7,7,7,7,7,7'"""

    p1_pits: str | None = None
    """P1's initial pit values as 7 comma-separated integers. Example: '7,7,7,7,7,7,7'"""

    p0_store: int = 0
    """P0's initial store value."""

    p1_store: int = 0
    """P1's initial store value."""

    starting_player: int = 0
    """Which player starts (0 or 1)."""


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


def parse_initial_state(config: Config) -> BoardState:
    """Parse initial state from config, returning initial or custom state."""
    if config.p0_pits is None and config.p1_pits is None:
        return BoardState.initial()

    # default to standard if only one side specified
    p0_pits = [int(x.strip()) for x in config.p0_pits.split(",")] if config.p0_pits else [7] * 7
    p1_pits = [int(x.strip()) for x in config.p1_pits.split(",")] if config.p1_pits else [7] * 7

    assert len(p0_pits) == 7, f"Expected 7 P0 pit values, got {len(p0_pits)}"
    assert len(p1_pits) == 7, f"Expected 7 P1 pit values, got {len(p1_pits)}"
    assert all(p >= 0 for p in p0_pits + p1_pits), "Pit values must be non-negative"
    assert config.p0_store >= 0 and config.p1_store >= 0, "Store values must be non-negative"
    assert config.starting_player in (0, 1), "starting_player must be 0 or 1"

    pits = p0_pits + p1_pits + [config.p0_store, config.p1_store]
    return BoardState.from_pits(pits, config.starting_player)


def run_terminal_game(config: Config, rules: RuleConfig) -> None:
    """Run the game in terminal mode."""
    state = parse_initial_state(config)
    solvers = [
        MinimaxSolver(rules, max_depth=config.p0_depth),
        MinimaxSolver(rules, max_depth=config.p1_depth),
    ]
    player_types = [config.p0, config.p1]

    print("Congkak - Terminal Mode")
    print("=" * 40)
    print(f"Rules: start={config.start_mode}, capture={config.capture}, forfeit={config.forfeit}")
    print(f"Players: P0={config.p0} (d={config.p0_depth}), P1={config.p1} (d={config.p1_depth})")
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
            move = solvers[current_player].get_best_move(state)
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


def _parse_start_mode(mode: str) -> StartMode:
    """Convert string start mode to Rust enum."""
    match mode:
        case "sequential":
            return StartMode.Sequential
        case "independent":
            return StartMode.SimultaneousIndependent
        case "leader_follower":
            return StartMode.SimultaneousLeaderFollower
        case _:
            raise ValueError(f"Unknown start mode: {mode}")


def _parse_leader_selection(sel: str) -> LeaderSelection:
    """Convert string leader selection to Rust enum."""
    match sel:
        case "random":
            return LeaderSelection.Random
        case "p0":
            return LeaderSelection.AlwaysP0
        case "p1":
            return LeaderSelection.AlwaysP1
        case _:
            raise ValueError(f"Unknown leader selection: {sel}")


def main(config: Config | None = None) -> None:
    """Main entry point."""
    if config is None:
        config = tyro.cli(Config)

    rules = RuleConfig(
        start_mode=_parse_start_mode(config.start_mode),
        leader_selection=_parse_leader_selection(config.leader_selection),
        capture_enabled=config.capture,
        forfeit_enabled=config.forfeit,
        burnt_holes_enabled=config.burnt_holes,
        capture_requires_loop=config.capture_requires_loop,
    )

    if config.gui:
        from congkak.gui.app import run_gui

        run_gui(
            p0_type=config.p0,
            p1_type=config.p1,
            p0_depth=config.p0_depth,
            p1_depth=config.p1_depth,
            rules=rules,
            animation_delay=config.animation_delay,
            initial_state=parse_initial_state(config),
        )
    else:
        run_terminal_game(config, rules)


if __name__ == "__main__":
    main()
