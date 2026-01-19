from congkak import BoardState


def test_initial_board() -> None:
    state = BoardState.initial()
    # 7 seeds in each pit, stores empty
    for i in range(7):
        assert state.pits[i] == 7
        assert state.pits[i + 7] == 7
    assert state.pits[14] == 0  # P0 store
    assert state.pits[15] == 0  # P1 store
    assert state.current_player == 0


def test_total_seeds() -> None:
    state = BoardState.initial()
    assert state.total_seeds() == 98  # 14 pits * 7 seeds


def test_board_hash() -> None:
    state1 = BoardState.initial()
    state2 = BoardState.initial()
    assert hash(state1) == hash(state2)
    assert state1 == state2


def test_player_pits() -> None:
    state = BoardState.initial()
    assert state.player_pits(0) == [7, 7, 7, 7, 7, 7, 7]
    assert state.player_pits(1) == [7, 7, 7, 7, 7, 7, 7]


def test_player_store_index() -> None:
    assert BoardState.player_store_index(0) == 14
    assert BoardState.player_store_index(1) == 15


def test_player_pit_range() -> None:
    assert BoardState.player_pit_range(0) == (0, 7)
    assert BoardState.player_pit_range(1) == (7, 14)


def test_from_pits() -> None:
    pits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 50, 60]
    state = BoardState.from_pits(pits, 1)
    assert list(state.pits) == pits
    assert state.current_player == 1
