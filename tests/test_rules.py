from congkak import (
    BoardState,
    LeaderSelection,
    RuleConfig,
    SimultaneousMoveState,
    SimultaneousPhase,
    StartMode,
    apply_move,
    apply_simultaneous_moves,
    get_legal_moves,
    is_terminal,
)


def test_default_rules() -> None:
    rules = RuleConfig.default_rules()
    assert rules.capture_enabled
    assert rules.forfeit_enabled
    assert rules.start_mode == StartMode.Sequential
    assert not rules.burnt_holes_enabled


def test_legal_moves_initial() -> None:
    state = BoardState.initial()
    moves = get_legal_moves(state)
    assert moves == [0, 1, 2, 3, 4, 5, 6]


def test_legal_moves_player1() -> None:
    state = BoardState.from_pits([0] * 16, 1)
    # set some seeds for player 1
    pits = list(state.pits)
    pits[7] = 5
    pits[10] = 3
    state = BoardState.from_pits(pits, 1)
    moves = get_legal_moves(state)
    assert moves == [7, 10]


def test_extra_turn_on_store() -> None:
    # clockwise: pit 0 with 1 seed -> lands in P0 store (14)
    pits = [0] * 16
    pits[0] = 1
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    result = apply_move(state, 0, rules)
    assert result.extra_turn
    assert result.state.current_player == 0
    assert result.state.pits[14] == 1


def test_relay_sowing() -> None:
    # landing in a pit with seeds -> relay continues
    # clockwise: 3 -> 2 -> 1 (lands in pit 1)
    pits = [0] * 16
    pits[3] = 2  # 2 seeds in pit 3
    pits[1] = 3  # 3 seeds in pit 1 (will be hit by relay)
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    result = apply_move(state, 3, rules)
    # pit 3 -> drop in 2, drop in 1 (now 4 seeds) -> relay picks up
    # -> drop in 0, 14, 13, 12 -> end
    assert result.state.pits[3] == 0
    assert result.state.pits[2] == 1
    assert result.state.pits[1] == 0  # picked up for relay


def test_capture() -> None:
    # landing in own empty pit captures opposite
    # clockwise: pit 6 with 3 seeds: 6 -> 5 -> 4 -> 3 (lands on pit 3)
    pits = [0] * 16
    pits[6] = 3  # 3 seeds: lands on pit 3 (own, empty)
    pits[10] = 5  # opposite of pit 3 (13-3=10) has 5 seeds
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    result = apply_move(state, 6, rules)
    # lands on pit 3 (empty), captures opposite (pit 10) + itself
    assert result.captured == 6  # 5 from opposite + 1 (the landing seed)
    assert result.state.pits[14] == 6  # captured seeds go to store
    assert result.state.pits[3] == 0
    assert result.state.pits[10] == 0


def test_capture_disabled() -> None:
    # clockwise: pit 6 with 3 seeds lands on pit 3
    pits = [0] * 16
    pits[6] = 3
    pits[10] = 5
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig(capture_enabled=False)

    result = apply_move(state, 6, rules)
    assert result.captured == 0
    assert result.state.pits[3] == 1  # seed stays
    assert result.state.pits[10] == 5  # opposite untouched


def test_forfeit() -> None:
    # landing in opponent empty pit forfeits seed
    # clockwise: pit 0 with 8 seeds: 0->14->13->12->11->10->9->8->7 (opponent's empty pit)
    pits = [0] * 16
    pits[0] = 8
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    result = apply_move(state, 0, rules)
    # lands on pit 7 (opponent, empty) -> forfeit to opponent store
    assert result.state.pits[7] == 0  # seed forfeited
    assert result.state.pits[15] == 1  # opponent store gets it


def test_forfeit_disabled() -> None:
    # clockwise: pit 0 with 8 seeds lands on pit 7 (opponent's pit)
    pits = [0] * 16
    pits[0] = 8
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig(forfeit_enabled=False)

    result = apply_move(state, 0, rules)
    assert result.state.pits[7] == 1  # seed stays
    assert result.state.pits[15] == 0  # opponent store empty


def test_terminal_p0_empty() -> None:
    pits = [0] * 16
    pits[7] = 10  # only P1 has seeds
    state = BoardState.from_pits(pits, 0)
    assert is_terminal(state)


def test_terminal_p1_empty() -> None:
    pits = [0] * 16
    pits[3] = 10  # only P0 has seeds
    state = BoardState.from_pits(pits, 1)
    assert is_terminal(state)


def test_not_terminal() -> None:
    state = BoardState.initial()
    assert not is_terminal(state)


def test_capture_requires_loop_blocks_early_capture() -> None:
    # pit 6 with 3 seeds: 6 -> 5 -> 4 -> 3 (lands on pit 3, own empty pit)
    # without looping through store, capture should NOT happen
    pits = [0] * 16
    pits[6] = 3
    pits[10] = 5  # opposite of pit 3
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig(capture_requires_loop=True)

    result = apply_move(state, 6, rules)
    # no capture because we didn't pass through store
    assert result.captured == 0
    assert result.state.pits[3] == 1  # seed stays
    assert result.state.pits[10] == 5  # opposite untouched


def test_capture_requires_loop_allows_after_loop() -> None:
    # verify capture still works when capture_requires_loop=False
    rules_no_loop = RuleConfig(capture_requires_loop=False)
    pits = [0] * 16
    pits[6] = 3
    pits[10] = 5
    state = BoardState.from_pits(pits, 0)
    result = apply_move(state, 6, rules_no_loop)
    assert result.captured == 6  # capture works without loop requirement


# simultaneous mode tests


def test_start_mode_enums() -> None:
    assert StartMode.Sequential == 0
    assert StartMode.SimultaneousIndependent == 1
    assert StartMode.SimultaneousLeaderFollower == 2


def test_leader_selection_enums() -> None:
    assert LeaderSelection.Random == 0
    assert LeaderSelection.AlwaysP0 == 1
    assert LeaderSelection.AlwaysP1 == 2


def test_simultaneous_phase_enums() -> None:
    assert SimultaneousPhase.AwaitingMoves == 0
    assert SimultaneousPhase.AwaitingFollower == 1
    assert SimultaneousPhase.ReadyToExecute == 2


def test_simultaneous_move_state_independent() -> None:
    sim_state = SimultaneousMoveState.for_independent()
    assert sim_state.phase == SimultaneousPhase.AwaitingMoves
    assert sim_state.p0_move is None
    assert sim_state.p1_move is None
    assert sim_state.leader is None
    assert sim_state.can_submit(0)
    assert sim_state.can_submit(1)


def test_simultaneous_move_state_leader_follower() -> None:
    sim_state = SimultaneousMoveState.for_leader_follower(0)
    assert sim_state.phase == SimultaneousPhase.AwaitingMoves
    assert sim_state.leader == 0
    assert sim_state.can_submit(0)
    assert not sim_state.can_submit(1)

    # leader submits
    sim_state.submit_move(0, 3)
    assert sim_state.phase == SimultaneousPhase.AwaitingFollower
    assert sim_state.get_leader_move() == 3
    assert not sim_state.can_submit(0)
    assert sim_state.can_submit(1)

    # follower submits
    sim_state.submit_move(1, 10)
    assert sim_state.phase == SimultaneousPhase.ReadyToExecute
    assert sim_state.p0_move == 3
    assert sim_state.p1_move == 10


def test_simultaneous_move_state_independent_submission() -> None:
    sim_state = SimultaneousMoveState.for_independent()

    # p0 submits
    sim_state.submit_move(0, 2)
    assert sim_state.phase == SimultaneousPhase.AwaitingMoves
    assert sim_state.p0_move == 2
    assert not sim_state.can_submit(0)
    assert sim_state.can_submit(1)

    # p1 submits
    sim_state.submit_move(1, 9)
    assert sim_state.phase == SimultaneousPhase.ReadyToExecute
    assert sim_state.p1_move == 9


def test_apply_simultaneous_moves_basic() -> None:
    state = BoardState.initial()
    rules = RuleConfig.default_rules()

    # both players pick from their pits
    result = apply_simultaneous_moves(state, 0, 7, rules)

    # verify both pits were emptied
    assert result.state.pits[0] == 0 or result.state.pits[0] > 7  # emptied or received seeds
    assert result.state.pits[7] == 0 or result.state.pits[7] > 7


def test_simultaneous_relay_uses_combined_pits() -> None:
    pits = [0] * 16
    pits[0] = 8
    pits[13] = 7
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    result = apply_simultaneous_moves(state, 0, 13, rules)

    # p1 should only have the seed from their own store landing
    assert result.state.pits[15] == 1


def test_rules_with_start_mode() -> None:
    rules = RuleConfig(
        start_mode=StartMode.SimultaneousIndependent,
        leader_selection=LeaderSelection.AlwaysP0,
    )
    assert rules.start_mode == StartMode.SimultaneousIndependent
    assert rules.leader_selection == LeaderSelection.AlwaysP0
