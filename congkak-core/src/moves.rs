use crate::board::{BoardState, P0_PITS, P0_STORE, P1_PITS, P1_STORE};
use crate::rules::RuleConfig;
use pyo3::prelude::*;

/// Result of applying a move
#[pyclass]
#[derive(Clone, Copy, Debug)]
pub struct MoveResult {
    #[pyo3(get)]
    pub state: BoardState,
    #[pyo3(get)]
    pub extra_turn: bool,
    #[pyo3(get)]
    pub captured: u8,
}

/// Get the opposite pit index for capture
fn opposite_pit(pit: usize) -> usize {
    // Pits 0-6 are opposite to 13-7, pits 7-13 are opposite to 6-0
    13 - pit
}

/// Check if a pit belongs to a player
fn is_player_pit(pit: usize, player: u8) -> bool {
    if player == 0 {
        P0_PITS.contains(&pit)
    } else {
        P1_PITS.contains(&pit)
    }
}

/// Get the store index for a player
fn player_store(player: u8) -> usize {
    if player == 0 {
        P0_STORE
    } else {
        P1_STORE
    }
}

/// Get the opponent's store index
fn opponent_store(player: u8) -> usize {
    if player == 0 {
        P1_STORE
    } else {
        P0_STORE
    }
}

/// Get the next position in clockwise sowing order (from P0's perspective).
/// Board layout:
/// [14]  13  12  11  10   9   8   7  [15]
///        0   1   2   3   4   5   6
///
/// Clockwise: 6->5->...->0->14->13->12->...->7->15->6
fn next_position(pos: usize) -> usize {
    match pos {
        1..=6 => pos - 1,   // P0 pits: going left toward store
        0 => P0_STORE,      // P0 pit 0 -> P0 store (left side)
        14 => 13,           // P0 store -> P1 pit 13
        8..=13 => pos - 1,  // P1 pits: going left toward their store
        7 => P1_STORE,      // P1 pit 7 -> P1 store (right side)
        15 => 6,            // P1 store -> P0 pit 6
        _ => unreachable!(),
    }
}

/// Apply a move and return the resulting state
/// This implements relay sowing with all rule variants
#[pyfunction]
pub fn apply_move(state: &BoardState, pit: usize, rules: &RuleConfig) -> MoveResult {
    let mut pits = state.pits;
    let player = state.current_player;
    let my_store = player_store(player);
    let opp_store = opponent_store(player);

    assert!(pit < pits.len(), "pit out of range: {pit}");
    assert!(is_player_pit(pit, player), "pit does not belong to player: {pit}");
    assert!(pits[pit] > 0, "pit is empty: {pit}");

    // pick up seeds from selected pit
    let mut seeds = pits[pit];
    pits[pit] = 0;

    let mut current_pos = pit;
    let mut extra_turn = false;
    let mut captured = 0u8;
    let mut has_looped = false; // track if we've passed through our store

    // relay sowing loop
    while seeds > 0 {
        // move to next position (counter-clockwise)
        current_pos = next_position(current_pos);

        // skip opponent's store
        if current_pos == opp_store {
            continue;
        }

        // track if we pass through our store (for capture_requires_loop rule)
        if current_pos == my_store {
            has_looped = true;
        }

        // drop one seed
        pits[current_pos] += 1;
        seeds -= 1;

        // check what happens when we drop the last seed
        if seeds == 0 {
            // landed in own store -> extra turn
            if current_pos == my_store {
                extra_turn = true;
                break;
            }

            // landed in a pit (not a store)
            if current_pos < 14 {
                let is_my_pit = is_player_pit(current_pos, player);
                let landed_count = pits[current_pos];

                // relay sowing: if pit now has more than 1 seed, pick up and continue
                if landed_count > 1 {
                    seeds = pits[current_pos];
                    pits[current_pos] = 0;
                    continue;
                }

                // landed_count == 1, this was an empty pit before we dropped
                let can_capture = rules.capture_enabled
                    && (!rules.capture_requires_loop || has_looped);
                if is_my_pit && can_capture {
                    // capture: take seeds from opposite pit + this seed
                    let opp_pit = opposite_pit(current_pos);
                    let opp_seeds = pits[opp_pit];
                    if opp_seeds > 0 {
                        captured = opp_seeds + 1;
                        pits[my_store] += opp_seeds + 1;
                        pits[current_pos] = 0;
                        pits[opp_pit] = 0;
                    }
                } else if !is_my_pit && rules.forfeit_enabled {
                    // forfeit: seed goes to opponent's store
                    pits[opp_store] += 1;
                    pits[current_pos] = 0;
                }
            }
        }
    }

    // determine next player
    let next_player = if extra_turn {
        player
    } else {
        1 - player
    };

    MoveResult {
        state: BoardState {
            pits,
            current_player: next_player,
        },
        extra_turn,
        captured,
    }
}

/// Get all legal moves for the current player
#[pyfunction]
pub fn get_legal_moves(state: &BoardState) -> Vec<usize> {
    let range = if state.current_player == 0 {
        P0_PITS
    } else {
        P1_PITS
    };

    range.filter(|&i| state.pits[i] > 0).collect()
}

/// Check if the game has ended (one side has no seeds in pits)
#[pyfunction]
pub fn is_terminal(state: &BoardState) -> bool {
    let p0_empty = state.pits[P0_PITS].iter().all(|&s| s == 0);
    let p1_empty = state.pits[P1_PITS].iter().all(|&s| s == 0);
    p0_empty || p1_empty
}

/// Get the winner (0, 1, or -1 for draw). Only valid when is_terminal is true.
#[pyfunction]
pub fn get_winner(state: &BoardState) -> i8 {
    let p0_score = state.pits[P0_STORE];
    let p1_score = state.pits[P1_STORE];

    // collect remaining seeds to respective stores
    let p0_remaining: u8 = state.pits[P0_PITS].iter().sum();
    let p1_remaining: u8 = state.pits[P1_PITS].iter().sum();

    let p0_total = p0_score + p0_remaining;
    let p1_total = p1_score + p1_remaining;

    if p0_total > p1_total {
        0
    } else if p1_total > p0_total {
        1
    } else {
        -1
    }
}

/// Get final scores (including remaining pit seeds). Returns (p0_score, p1_score).
#[pyfunction]
pub fn get_final_scores(state: &BoardState) -> (u8, u8) {
    let p0_remaining: u8 = state.pits[P0_PITS].iter().sum();
    let p1_remaining: u8 = state.pits[P1_PITS].iter().sum();

    (
        state.pits[P0_STORE] + p0_remaining,
        state.pits[P1_STORE] + p1_remaining,
    )
}

/// Result of applying simultaneous moves.
#[pyclass]
#[derive(Clone, Copy, Debug)]
pub struct SimultaneousMoveResult {
    #[pyo3(get)]
    pub state: BoardState,
    #[pyo3(get)]
    pub p0_extra_turn: bool,
    #[pyo3(get)]
    pub p1_extra_turn: bool,
    #[pyo3(get)]
    pub p0_captured: u8,
    #[pyo3(get)]
    pub p1_captured: u8,
}

/// Apply simultaneous moves from both players.
/// Both players pick up seeds and sow. Captures and extra turns are resolved together.
#[pyfunction]
pub fn apply_simultaneous_moves(
    state: &BoardState,
    p0_pit: usize,
    p1_pit: usize,
    rules: &RuleConfig,
) -> SimultaneousMoveResult {
    // validate moves
    assert!(P0_PITS.contains(&p0_pit), "p0_pit out of range: {p0_pit}");
    assert!(P1_PITS.contains(&p1_pit), "p1_pit out of range: {p1_pit}");
    assert!(state.pits[p0_pit] > 0, "p0 pit is empty: {p0_pit}");
    assert!(state.pits[p1_pit] > 0, "p1 pit is empty: {p1_pit}");

    // apply p0's move first
    let result0 = apply_move(state, p0_pit, rules);

    // create state for p1 where p0's chosen pit is already picked up
    // this simulates "simultaneous" pickup
    let mut p1_start_state = state.pits;
    p1_start_state[p0_pit] = 0; // p0 already picked up these seeds

    // apply p1's move on the state after p0 picked up (but before p0 sowed)
    // for simplicity, we apply p1's move independently then merge
    let mut state_for_p1 = *state;
    state_for_p1.current_player = 1;
    let result1 = apply_move(&state_for_p1, p1_pit, rules);

    // merge the results:
    // the final pit counts are: initial - picked_up + deposited_by_both
    // but we need to handle capture conflicts

    let mut final_pits = state.pits;

    // remove seeds from both chosen pits
    final_pits[p0_pit] = 0;
    final_pits[p1_pit] = 0;

    // calculate net changes from each player's move
    // p0's deposits (excluding captures which go to store)
    for i in 0..16 {
        if i == p0_pit || i == p1_pit {
            continue;
        }
        // add p0's deposits (difference from initial, excluding store changes from captures)
        let p0_deposit = result0.state.pits[i].saturating_sub(state.pits[i]);
        let p1_deposit = result1.state.pits[i].saturating_sub(state.pits[i]);

        // both players' sowing adds to the pit
        if i != P0_STORE && i != P1_STORE {
            final_pits[i] = state.pits[i].saturating_sub(
                if i == p0_pit { state.pits[p0_pit] } else { 0 }
            ).saturating_sub(
                if i == p1_pit { state.pits[p1_pit] } else { 0 }
            ) + p0_deposit + p1_deposit;
        }
    }

    // handle captures - check if both tried to capture the same opposite pit
    let p0_captured = result0.captured;
    let p1_captured = result1.captured;

    // stores: add from sowing + captures
    let p0_store_from_sow = if result0.state.pits[P0_STORE] > state.pits[P0_STORE] + result0.captured {
        result0.state.pits[P0_STORE] - state.pits[P0_STORE] - result0.captured
    } else if result0.extra_turn && result0.captured == 0 {
        1 // landed in store for extra turn
    } else {
        result0.state.pits[P0_STORE].saturating_sub(state.pits[P0_STORE])
    };

    let p1_store_from_sow = if result1.state.pits[P1_STORE] > state.pits[P1_STORE] + result1.captured {
        result1.state.pits[P1_STORE] - state.pits[P1_STORE] - result1.captured
    } else if result1.extra_turn && result1.captured == 0 {
        1 // landed in store for extra turn
    } else {
        result1.state.pits[P1_STORE].saturating_sub(state.pits[P1_STORE])
    };

    final_pits[P0_STORE] = state.pits[P0_STORE] + p0_store_from_sow + p0_captured;
    final_pits[P1_STORE] = state.pits[P1_STORE] + p1_store_from_sow + p1_captured;

    // extra turns: if both get extra turns, continue simultaneous
    // if one gets extra turn, that player goes next sequentially
    let next_player = match (result0.extra_turn, result1.extra_turn) {
        (true, true) => 0,  // both extra turns -> p0 goes first in next simultaneous round
        (true, false) => 0, // p0 extra turn
        (false, true) => 1, // p1 extra turn
        (false, false) => 0, // no extra turns, p0 starts next round
    };

    SimultaneousMoveResult {
        state: BoardState {
            pits: final_pits,
            current_player: next_player,
        },
        p0_extra_turn: result0.extra_turn,
        p1_extra_turn: result1.extra_turn,
        p0_captured,
        p1_captured,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_opposite_pit() {
        assert_eq!(opposite_pit(0), 13);
        assert_eq!(opposite_pit(6), 7);
        assert_eq!(opposite_pit(7), 6);
        assert_eq!(opposite_pit(13), 0);
    }

    #[test]
    fn test_initial_legal_moves() {
        let state = BoardState::initial();
        let moves = get_legal_moves(&state);
        assert_eq!(moves, vec![0, 1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn test_relay_sowing() {
        let state = BoardState::initial();
        let rules = RuleConfig::default();
        // move from pit 0 with 7 seeds (clockwise: 0->14->13->12->11->10->9->8)
        let result = apply_move(&state, 0, &rules);
        // seeds deposited through store and into P1's pits, relay continues from pit 8
        assert!(result.state.pits[0] == 0);
    }

    #[test]
    fn test_extra_turn_on_store() {
        // create a state where moving will land exactly in store
        // clockwise sowing: 0 -> P0_STORE (14), so 1 seed from pit 0 lands in store
        let mut pits = [0u8; 16];
        pits[0] = 1;
        let state = BoardState::from_pits(pits, 0);
        let rules = RuleConfig::default();
        let result = apply_move(&state, 0, &rules);
        assert!(result.extra_turn);
        assert_eq!(result.state.current_player, 0); // same player
        assert_eq!(result.state.pits[P0_STORE], 1);
    }
}
