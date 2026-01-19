use pyo3::prelude::*;
use std::hash::{Hash, Hasher};

/// Board indices:
/// - 0-6: Player 0's pits (left to right from their perspective)
/// - 7-13: Player 1's pits (left to right from their perspective)
/// - 14: Player 0's store
/// - 15: Player 1's store
pub const P0_PITS: std::ops::Range<usize> = 0..7;
pub const P1_PITS: std::ops::Range<usize> = 7..14;
pub const P0_STORE: usize = 14;
pub const P1_STORE: usize = 15;
pub const INITIAL_SEEDS: u8 = 7;

#[pyclass]
#[derive(Clone, Copy, Eq, PartialEq, Debug)]
pub struct BoardState {
    #[pyo3(get)]
    pub pits: [u8; 16],
    #[pyo3(get)]
    pub current_player: u8,
}

impl Hash for BoardState {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.pits.hash(state);
        self.current_player.hash(state);
    }
}

#[pymethods]
impl BoardState {
    #[new]
    pub fn new() -> Self {
        Self::initial()
    }

    #[staticmethod]
    pub fn initial() -> Self {
        let mut pits = [INITIAL_SEEDS; 16];
        pits[P0_STORE] = 0;
        pits[P1_STORE] = 0;
        BoardState {
            pits,
            current_player: 0,
        }
    }

    #[staticmethod]
    pub fn from_pits(pits: [u8; 16], current_player: u8) -> Self {
        BoardState {
            pits,
            current_player,
        }
    }

    pub fn get_store(&self, player: u8) -> u8 {
        if player == 0 {
            self.pits[P0_STORE]
        } else {
            self.pits[P1_STORE]
        }
    }

    pub fn get_pit(&self, index: usize) -> u8 {
        self.pits[index]
    }

    pub fn player_pits(&self, player: u8) -> Vec<u8> {
        if player == 0 {
            self.pits[P0_PITS].to_vec()
        } else {
            self.pits[P1_PITS].to_vec()
        }
    }

    #[staticmethod]
    pub fn player_store_index(player: u8) -> usize {
        if player == 0 {
            P0_STORE
        } else {
            P1_STORE
        }
    }

    #[staticmethod]
    pub fn player_pit_range(player: u8) -> (usize, usize) {
        if player == 0 {
            (P0_PITS.start, P0_PITS.end)
        } else {
            (P1_PITS.start, P1_PITS.end)
        }
    }

    pub fn total_seeds(&self) -> u8 {
        self.pits.iter().sum()
    }

    fn __hash__(&self) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.pits == other.pits && self.current_player == other.current_player
    }

    fn __repr__(&self) -> String {
        format!(
            "BoardState(pits={:?}, current_player={})",
            self.pits, self.current_player
        )
    }
}

impl Default for BoardState {
    fn default() -> Self {
        Self::initial()
    }
}
