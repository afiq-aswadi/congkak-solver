from congkak.congkak_core import BoardState


def simple_eval(state: BoardState, player: int) -> float:
    """Simple evaluation: difference in store seeds."""
    my_store = state.get_store(player)
    opp_store = state.get_store(1 - player)
    return float(my_store - opp_store)


def weighted_eval(state: BoardState, player: int) -> float:
    """Weighted evaluation considering stores and pit positions.

    Weights pit seeds less than store seeds since they can still be lost.
    Also gives slight bonus to pits that can reach the store in one move.
    """
    my_store = state.get_store(player)
    opp_store = state.get_store(1 - player)

    my_pits = state.player_pits(player)
    opp_pits = state.player_pits(1 - player)

    # pit seeds worth less than store seeds
    pit_weight = 0.5
    my_pit_total = sum(my_pits)
    opp_pit_total = sum(opp_pits)

    # bonus for pits that can land in store (pit i with i+1 seeds for player 0)
    store_reach_bonus = 0.0
    for i, seeds in enumerate(my_pits):
        distance_to_store = 7 - i  # for player 0
        if player == 1:
            distance_to_store = 7 - i
        if seeds == distance_to_store:
            store_reach_bonus += 0.5

    score = (my_store - opp_store) + pit_weight * (my_pit_total - opp_pit_total) + store_reach_bonus
    return score
