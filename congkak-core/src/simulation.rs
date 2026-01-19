use crate::board::BoardState;
use crate::moves::{apply_move, get_legal_moves, is_terminal};
use crate::rules::RuleConfig;
use pyo3::prelude::*;

/// Play a random game and return the winner
#[pyfunction]
pub fn random_playout(state: &BoardState, rules: &RuleConfig, seed: u64) -> i8 {
    let mut current = *state;
    let mut rng_state = if seed == 0 { 0x9E3779B97F4A7C15 } else { seed };

    while !is_terminal(&current) {
        let moves = get_legal_moves(&current);
        if moves.is_empty() {
            break;
        }

        // simple xorshift for random selection
        rng_state ^= rng_state << 13;
        rng_state ^= rng_state >> 7;
        rng_state ^= rng_state << 17;

        let idx = (rng_state as usize) % moves.len();
        let result = apply_move(&current, moves[idx], rules);
        current = result.state;
    }

    crate::moves::get_winner(&current)
}

/// Run multiple random playouts and return win counts [p0_wins, p1_wins, draws]
#[pyfunction]
pub fn batch_random_playouts(
    state: &BoardState,
    rules: &RuleConfig,
    num_playouts: u32,
    base_seed: u64,
) -> [u32; 3] {
    let mut counts = [0u32; 3];

    for i in 0..num_playouts {
        let winner = random_playout(state, rules, base_seed.wrapping_add(i as u64));
        match winner {
            0 => counts[0] += 1,
            1 => counts[1] += 1,
            _ => counts[2] += 1,
        }
    }

    counts
}

/// Perft: count positions at depth (for debugging move generation)
#[pyfunction]
pub fn perft(state: &BoardState, rules: &RuleConfig, depth: u32) -> u64 {
    if depth == 0 || is_terminal(state) {
        return 1;
    }

    let moves = get_legal_moves(state);
    let mut count = 0u64;

    for m in moves {
        let result = apply_move(state, m, rules);
        count += perft(&result.state, rules, depth - 1);
    }

    count
}
