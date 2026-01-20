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

fn apply_move_internal(
    state: &BoardState,
    pit: usize,
    rules: &RuleConfig,
) -> (MoveResult, u32) {
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
    let mut steps = 0u32;

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
        steps += 1;

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

    let result = MoveResult {
        state: BoardState {
            pits,
            current_player: next_player,
        },
        extra_turn,
        captured,
    };

    (result, steps)
}

/// Apply a move and return the resulting state
/// This implements relay sowing with all rule variants
#[pyfunction]
pub fn apply_move(state: &BoardState, pit: usize, rules: &RuleConfig) -> MoveResult {
    let (result, _) = apply_move_internal(state, pit, rules);
    result
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

struct SimPlayerState {
    player: u8,
    current_pos: usize,
    seeds: u8,
    delta: [i16; 16],
    done: bool,
    extra_turn: bool,
    has_looped: bool,
    steps: u32,
    captured: u8,
    my_store: usize,
    opp_store: usize,
}

impl SimPlayerState {
    fn new(player: u8, start_pit: usize, base_pits: &[u8; 16]) -> Self {
        let seeds = base_pits[start_pit];
        assert!(seeds > 0, "start pit is empty: {start_pit}");
        let mut delta = [0i16; 16];
        delta[start_pit] = -(seeds as i16);
        Self {
            player,
            current_pos: start_pit,
            seeds,
            delta,
            done: false,
            extra_turn: false,
            has_looped: false,
            steps: 0,
            captured: 0,
            my_store: player_store(player),
            opp_store: opponent_store(player),
        }
    }

    fn step(&mut self) {
        if self.done || self.seeds == 0 {
            return;
        }

        self.current_pos = next_position(self.current_pos);
        while self.current_pos == self.opp_store {
            self.current_pos = next_position(self.current_pos);
        }

        if self.current_pos == self.my_store {
            self.has_looped = true;
        }

        self.delta[self.current_pos] += 1;
        self.seeds -= 1;
        self.steps += 1;

        if self.seeds == 0 && self.current_pos == self.my_store {
            self.extra_turn = true;
            self.done = true;
        }
    }

    fn check_end_conditions(
        &mut self,
        base_pits: &[u8; 16],
        other_delta: &[i16; 16],
        rules: &RuleConfig,
    ) {
        if self.done || self.seeds > 0 {
            return;
        }

        let pos = self.current_pos;
        if pos >= 14 {
            self.done = true;
            return;
        }

        let actual_count = base_pits[pos] as i16 + self.delta[pos] + other_delta[pos];
        assert!(actual_count >= 0, "pit underflow at index {pos}");

        if actual_count > 1 {
            self.seeds = actual_count as u8;
            self.delta[pos] = -(base_pits[pos] as i16) - other_delta[pos];
            return;
        }

        let is_my_pit = is_player_pit(pos, self.player);
        let can_capture = rules.capture_enabled
            && (!rules.capture_requires_loop || self.has_looped);
        if is_my_pit && can_capture {
            let opp_pit = opposite_pit(pos);
            let opp_actual =
                base_pits[opp_pit] as i16 + self.delta[opp_pit] + other_delta[opp_pit];
            assert!(opp_actual >= 0, "pit underflow at index {opp_pit}");
            if opp_actual > 0 {
                let captured = (opp_actual + 1) as u8;
                self.captured = self.captured.saturating_add(captured);
                self.delta[self.my_store] += captured as i16;
                self.delta[pos] = -(base_pits[pos] as i16) - other_delta[pos];
                self.delta[opp_pit] = -(base_pits[opp_pit] as i16) - other_delta[opp_pit];
                self.done = true;
                return;
            }
        } else if !is_my_pit && rules.forfeit_enabled {
            self.delta[self.opp_store] += 1;
            self.delta[pos] = -(base_pits[pos] as i16) - other_delta[pos];
            self.done = true;
            return;
        }

        self.done = true;
    }
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

    let base_pits = state.pits;
    let mut p0_state = SimPlayerState::new(0, p0_pit, &base_pits);
    let mut p1_state = SimPlayerState::new(1, p1_pit, &base_pits);

    // run sowing in lock-step so relay/capture/forfeit sees the combined board.
    while !(p0_state.done && p1_state.done) {
        p0_state.step();
        p1_state.step();

        if p0_state.seeds == 0 && !p0_state.done {
            p0_state.check_end_conditions(&base_pits, &p1_state.delta, rules);
        }
        if p1_state.seeds == 0 && !p1_state.done {
            p1_state.check_end_conditions(&base_pits, &p0_state.delta, rules);
        }
    }

    let mut final_pits = [0u8; 16];
    for i in 0..16 {
        let combined = base_pits[i] as i16 + p0_state.delta[i] + p1_state.delta[i];
        assert!(combined >= 0, "combined pit underflow at index {i}");
        assert!(combined <= u8::MAX as i16, "combined pit overflow at index {i}");
        final_pits[i] = combined as u8;
    }

    let initial_total: u16 = state.pits.iter().map(|&v| v as u16).sum();
    let final_total: u16 = final_pits.iter().map(|&v| v as u16).sum();
    assert!(
        initial_total == final_total,
        "seed count changed: {initial_total} -> {final_total}"
    );

    let next_player = match (p0_state.extra_turn, p1_state.extra_turn) {
        (true, false) => 0,
        (false, true) => 1,
        _ => {
            if p0_state.steps < p1_state.steps {
                0
            } else if p1_state.steps < p0_state.steps {
                1
            } else {
                let mut tie_state = (p0_pit as u64) << 32 | p1_pit as u64;
                tie_state ^= tie_state << 13;
                tie_state ^= tie_state >> 7;
                tie_state ^= tie_state << 17;
                (tie_state & 1) as u8
            }
        }
    };

    SimultaneousMoveResult {
        state: BoardState {
            pits: final_pits,
            current_player: next_player,
        },
        p0_extra_turn: p0_state.extra_turn,
        p1_extra_turn: p1_state.extra_turn,
        p0_captured: p0_state.captured,
        p1_captured: p1_state.captured,
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

    #[test]
    fn test_simultaneous_preserves_selected_pit_deposit() {
        let mut pits = [0u8; 16];
        pits[0] = 7;
        pits[13] = 7;
        let state = BoardState::from_pits(pits, 0);
        let rules = RuleConfig::default();
        let result = apply_simultaneous_moves(&state, 0, 13, &rules);

        assert_eq!(result.state.pits[13], 1);
    }

    #[test]
    fn test_simultaneous_forfeit_uses_emptied_opponent_pit() {
        let mut pits = [0u8; 16];
        pits[0] = 8;
        pits[7] = 1;
        let state = BoardState::from_pits(pits, 0);
        let rules = RuleConfig::default();
        let result = apply_simultaneous_moves(&state, 0, 7, &rules);

        assert_eq!(result.state.pits[7], 0);
        assert_eq!(result.state.pits[P1_STORE], 2);
    }

    #[test]
    fn test_simultaneous_capture_clears_pit() {
        let mut pits = [0u8; 16];
        pits[4] = 1;
        pits[7] = 1;
        pits[10] = 5;
        let state = BoardState::from_pits(pits, 0);
        let rules = RuleConfig::default();
        let result = apply_simultaneous_moves(&state, 4, 7, &rules);

        assert_eq!(result.state.pits[10], 0);
        assert_eq!(result.state.pits[P0_STORE], 6);
    }
}
