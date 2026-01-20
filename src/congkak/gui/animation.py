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


@dataclass
class SimultaneousSowingStep:
    """A single step in simultaneous sowing animation."""

    pits: list[int]  # combined board state
    p0_seeds_in_hand: int
    p1_seeds_in_hand: int
    p0_current_pos: int | None  # None if picking up or done
    p1_current_pos: int | None
    p0_action: str  # pickup/drop/relay/capture/forfeit/extra_turn/done/waiting
    p1_action: str


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
    has_looped = False  # track if we've passed through our store

    while seeds > 0:
        current_pos = next_position(current_pos)

        # skip opponent's store
        if current_pos == opp_store:
            continue

        # track if we pass through our store
        if current_pos == my_store:
            has_looped = True

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
                can_capture = rules.capture_enabled and (
                    not rules.capture_requires_loop or has_looped
                )
                if is_my_pit and can_capture:
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


class _PlayerSowingState:
    """Internal class to track one player's sowing progress."""

    def __init__(
        self, player: int, start_pit: int, initial_pits: list[int], rules: RuleConfig
    ) -> None:
        self.player = player
        self.current_pos = start_pit
        self.seeds = initial_pits[start_pit]
        self.delta = [0] * 16  # changes this player makes to the board
        self.delta[start_pit] = -initial_pits[start_pit]  # pick up seeds
        self.rules = rules
        self.my_store = player_store(player)
        self.opp_store = opponent_store(player)
        self.done = False
        self.extra_turn = False
        self.has_looped = False
        self.last_action = "pickup"
        self.last_pos: int | None = None

    def step(self) -> str:
        """Advance by one drop. Returns the action taken."""
        if self.done:
            return "waiting"

        if self.seeds == 0:
            self.done = True
            return "done"

        # move to next position
        self.current_pos = next_position(self.current_pos)

        # skip opponent's store
        while self.current_pos == self.opp_store:
            self.current_pos = next_position(self.current_pos)

        # track if we pass through our store
        if self.current_pos == self.my_store:
            self.has_looped = True

        # drop one seed
        self.delta[self.current_pos] += 1
        self.seeds -= 1
        self.last_pos = self.current_pos
        action = "drop"

        # check what happens when we drop the last seed
        if self.seeds == 0:
            # landed in own store -> extra turn
            if self.current_pos == self.my_store:
                self.extra_turn = True
                self.done = True
                return "extra_turn"

            # landed in a pit (not a store)
            if self.current_pos < 14:
                # need to check the actual pit count (base + our delta only for relay check)
                # for relay: we only relay if there were seeds there before we dropped
                # this is tracked via delta - if delta > 1, there were seeds before
                return action

        self.last_action = action
        return action

    def check_end_conditions(self, base_pits: list[int], other_delta: list[int]) -> str:
        """Check end-of-sowing conditions after both players have stepped.

        Must be called only when seeds == 0 and not yet done.
        Returns the final action: relay, capture, forfeit, or done.
        """
        if self.done or self.seeds > 0:
            return "waiting" if self.done else "drop"

        pos = self.current_pos
        if pos >= 14:  # in a store, already handled
            self.done = True
            return "done"

        # calculate actual pit count: base + our delta + other's delta
        actual_count = base_pits[pos] + self.delta[pos] + other_delta[pos]

        # relay: if pit now has more than 1 seed
        if actual_count > 1:
            self.seeds = actual_count
            # reset delta for this pit (we're picking up everything)
            self.delta[pos] = -base_pits[pos] - other_delta[pos]
            return "relay"

        # landed on empty pit (count == 1, it was empty before)
        is_my_pit = is_player_pit(pos, self.player)
        can_capture = self.rules.capture_enabled and (
            not self.rules.capture_requires_loop or self.has_looped
        )

        if is_my_pit and can_capture:
            opp_pit = opposite_pit(pos)
            opp_actual = base_pits[opp_pit] + self.delta[opp_pit] + other_delta[opp_pit]
            if opp_actual > 0:
                # capture: take opponent's seeds + our seed
                captured = opp_actual + 1
                self.delta[self.my_store] += captured
                self.delta[pos] = -base_pits[pos] - other_delta[pos]
                self.delta[opp_pit] = -base_pits[opp_pit] - other_delta[opp_pit]
                self.done = True
                return "capture"
        elif not is_my_pit and self.rules.forfeit_enabled:
            # forfeit: seed goes to opponent's store
            self.delta[self.opp_store] += 1
            self.delta[pos] = -base_pits[pos] - other_delta[pos]
            self.done = True
            return "forfeit"

        self.done = True
        return "done"


def animate_simultaneous_sowing(
    state: BoardState, p0_pit: int, p1_pit: int, rules: RuleConfig
) -> Generator[SimultaneousSowingStep, None, tuple[bool, bool]]:
    """Generate animation steps for simultaneous sowing.

    Returns (p0_extra_turn, p1_extra_turn) when complete.
    """
    base_pits = list(state.pits)
    p0_state = _PlayerSowingState(0, p0_pit, base_pits, rules)
    p1_state = _PlayerSowingState(1, p1_pit, base_pits, rules)

    def combined_pits() -> list[int]:
        return [base_pits[i] + p0_state.delta[i] + p1_state.delta[i] for i in range(16)]

    # yield initial pickup state
    yield SimultaneousSowingStep(
        pits=combined_pits(),
        p0_seeds_in_hand=p0_state.seeds,
        p1_seeds_in_hand=p1_state.seeds,
        p0_current_pos=None,
        p1_current_pos=None,
        p0_action="pickup",
        p1_action="pickup",
    )

    # sowing loop - advance both players in lock-step
    while not (p0_state.done and p1_state.done):
        # each player takes one step
        p0_action = p0_state.step()
        p1_action = p1_state.step()

        # yield intermediate state after dropping
        yield SimultaneousSowingStep(
            pits=combined_pits(),
            p0_seeds_in_hand=p0_state.seeds,
            p1_seeds_in_hand=p1_state.seeds,
            p0_current_pos=p0_state.last_pos,
            p1_current_pos=p1_state.last_pos,
            p0_action=p0_action,
            p1_action=p1_action,
        )

        # check end conditions for players who just ran out of seeds
        if p0_state.seeds == 0 and not p0_state.done:
            p0_end_action = p0_state.check_end_conditions(base_pits, p1_state.delta)
            if p0_end_action in ("relay", "capture", "forfeit"):
                yield SimultaneousSowingStep(
                    pits=combined_pits(),
                    p0_seeds_in_hand=p0_state.seeds,
                    p1_seeds_in_hand=p1_state.seeds,
                    p0_current_pos=p0_state.last_pos,
                    p1_current_pos=p1_state.last_pos,
                    p0_action=p0_end_action,
                    p1_action="waiting" if p1_state.done else p1_action,
                )

        if p1_state.seeds == 0 and not p1_state.done:
            p1_end_action = p1_state.check_end_conditions(base_pits, p0_state.delta)
            if p1_end_action in ("relay", "capture", "forfeit"):
                yield SimultaneousSowingStep(
                    pits=combined_pits(),
                    p0_seeds_in_hand=p0_state.seeds,
                    p1_seeds_in_hand=p1_state.seeds,
                    p0_current_pos=p0_state.last_pos,
                    p1_current_pos=p1_state.last_pos,
                    p0_action="waiting" if p0_state.done else p0_action,
                    p1_action=p1_end_action,
                )

    # final done state
    yield SimultaneousSowingStep(
        pits=combined_pits(),
        p0_seeds_in_hand=0,
        p1_seeds_in_hand=0,
        p0_current_pos=None,
        p1_current_pos=None,
        p0_action="done",
        p1_action="done",
    )

    return (p0_state.extra_turn, p1_state.extra_turn)
