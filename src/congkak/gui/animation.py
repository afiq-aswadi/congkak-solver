from collections.abc import Generator
from dataclasses import dataclass

from congkak.congkak_core import BoardState, RuleConfig

P0_PITS = range(0, 7)
P1_PITS = range(7, 14)
P0_STORE = 14
P1_STORE = 15


def next_position(pos: int) -> int:
    """Get next position in clockwise sowing order."""
    if 1 <= pos <= 6:
        return pos - 1
    elif pos == 0:
        return P0_STORE
    elif pos == 14:
        return 13
    elif 8 <= pos <= 13:
        return pos - 1
    elif pos == 7:
        return P1_STORE
    elif pos == 15:
        return 6
    raise ValueError(f"Invalid position: {pos}")


def opposite_pit(pit: int) -> int:
    """Get the opposite pit for capture."""
    return 13 - pit


def is_player_pit(pit: int, player: int) -> bool:
    """Check if pit belongs to player."""
    if player == 0:
        return pit in P0_PITS
    return pit in P1_PITS


def player_store(player: int) -> int:
    """Get store index for player."""
    return P0_STORE if player == 0 else P1_STORE


def opponent_store(player: int) -> int:
    """Get opponent's store index."""
    return P1_STORE if player == 0 else P0_STORE


@dataclass
class SowingStep:
    """A single step in the sowing animation."""

    pits: list[int]
    seeds_in_hand: int
    current_pos: int | None  # position where we just dropped, None if picking up
    action: str  # "pickup", "drop", "relay", "capture", "forfeit", "extra_turn", "done"


def animate_sowing(
    state: BoardState, pit: int, rules: RuleConfig
) -> Generator[SowingStep, None, None]:
    """Generate animation steps for a sowing move."""
    pits = list(state.pits)
    player = state.current_player
    my_store = player_store(player)
    opp_store = opponent_store(player)

    # pick up seeds
    seeds = pits[pit]
    pits[pit] = 0
    yield SowingStep(pits.copy(), seeds, None, "pickup")

    current_pos = pit

    while seeds > 0:
        current_pos = next_position(current_pos)

        # skip opponent's store
        if current_pos == opp_store:
            continue

        # drop one seed
        pits[current_pos] += 1
        seeds -= 1
        yield SowingStep(pits.copy(), seeds, current_pos, "drop")

        # check what happens when we drop the last seed
        if seeds == 0:
            # landed in own store -> extra turn
            if current_pos == my_store:
                yield SowingStep(pits.copy(), 0, current_pos, "extra_turn")
                break

            # landed in a pit (not a store)
            if current_pos < 14:
                is_my_pit = is_player_pit(current_pos, player)
                landed_count = pits[current_pos]

                # relay sowing: if pit now has more than 1 seed, pick up and continue
                if landed_count > 1:
                    seeds = pits[current_pos]
                    pits[current_pos] = 0
                    yield SowingStep(pits.copy(), seeds, current_pos, "relay")
                    continue

                # landed_count == 1, this was an empty pit before we dropped
                if is_my_pit and rules.capture_enabled:
                    opp_pit = opposite_pit(current_pos)
                    opp_seeds = pits[opp_pit]
                    if opp_seeds > 0:
                        captured = opp_seeds + 1
                        pits[my_store] += captured
                        pits[current_pos] = 0
                        pits[opp_pit] = 0
                        yield SowingStep(pits.copy(), 0, current_pos, "capture")
                elif not is_my_pit and rules.forfeit_enabled:
                    pits[opp_store] += 1
                    pits[current_pos] = 0
                    yield SowingStep(pits.copy(), 0, current_pos, "forfeit")

    yield SowingStep(pits.copy(), 0, None, "done")
