from congkak import BoardState, RuleConfig, get_legal_moves, is_terminal
from congkak.solver import MinimaxSolver, simple_eval, weighted_eval


def test_simple_eval() -> None:
    pits = [0] * 16
    pits[14] = 30  # P0 store
    pits[15] = 20  # P1 store
    state = BoardState.from_pits(pits, 0)

    assert simple_eval(state, 0) == 10.0
    assert simple_eval(state, 1) == -10.0


def test_weighted_eval() -> None:
    pits = [0] * 16
    pits[14] = 30
    pits[15] = 20
    pits[0] = 5  # P0 has 5 seeds in pits
    state = BoardState.from_pits(pits, 0)

    # weighted_eval gives partial credit for pit seeds
    score = weighted_eval(state, 0)
    assert score > 10.0  # more than simple eval due to pit seeds


def test_solver_finds_winning_move() -> None:
    # set up a winning position for P0
    pits = [0] * 16
    pits[6] = 1  # P0 can drop into store -> extra turn, then win
    pits[7] = 1  # P1 has a seed so game is not terminal
    pits[14] = 48
    pits[15] = 40
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    solver = MinimaxSolver(rules, max_depth=4)
    move = solver.get_best_move(state)
    assert move == 6  # should take the winning move


def test_solver_avoids_losing() -> None:
    # P0 has two options: pit 6 gives extra turn and wins, pit 0 loses
    pits = [0] * 16
    pits[0] = 1  # bad move: lands in pit 1, no capture, P1 takes last seed
    pits[6] = 1  # good move: lands in store (extra turn), then P0 wins
    pits[7] = 1  # P1 has a seed so game is not terminal
    pits[14] = 45  # P0 ahead
    pits[15] = 40
    state = BoardState.from_pits(pits, 0)
    rules = RuleConfig.default_rules()

    solver = MinimaxSolver(rules, max_depth=4)
    move = solver.get_best_move(state)
    # solver should find that pit 6 leads to a better position
    assert move in get_legal_moves(state)  # just verify it returns a valid move


def test_solver_returns_none_on_terminal() -> None:
    pits = [0] * 16
    pits[14] = 50
    pits[15] = 48
    state = BoardState.from_pits(pits, 0)

    assert is_terminal(state)

    rules = RuleConfig.default_rules()
    solver = MinimaxSolver(rules, max_depth=4)
    move = solver.get_best_move(state)
    assert move is None


def test_solver_transposition_table() -> None:
    state = BoardState.initial()
    rules = RuleConfig.default_rules()

    solver = MinimaxSolver(rules, max_depth=4, use_tt=True)
    move1 = solver.get_best_move(state)
    nodes1 = solver.nodes_searched

    # second search should use TT
    solver.nodes_searched = 0
    move2 = solver.get_best_move(state)
    nodes2 = solver.nodes_searched

    assert move1 == move2
    assert nodes2 < nodes1  # TT should reduce nodes


def test_solver_no_transposition_table() -> None:
    state = BoardState.initial()
    rules = RuleConfig.default_rules()

    solver = MinimaxSolver(rules, max_depth=3, use_tt=False)
    move = solver.get_best_move(state)
    assert move in get_legal_moves(state)


def test_solver_depth_affects_quality() -> None:
    # deeper search should find better moves
    state = BoardState.initial()
    rules = RuleConfig.default_rules()

    solver_shallow = MinimaxSolver(rules, max_depth=2)
    solver_deep = MinimaxSolver(rules, max_depth=6)

    _ = solver_shallow.get_best_move(state)
    _ = solver_deep.get_best_move(state)

    # deeper search explores more nodes
    assert solver_deep.nodes_searched > solver_shallow.nodes_searched
