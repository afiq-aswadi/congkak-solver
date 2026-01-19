use pyo3::prelude::*;

/// Start mode for the first move(s) of the game.
#[pyclass(eq, eq_int)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum StartMode {
    /// Standard sequential play: player 0 moves, then player 1.
    #[default]
    Sequential = 0,
    /// Both players select moves simultaneously without seeing each other's choice.
    SimultaneousIndependent = 1,
    /// Leader commits first, follower sees leader's choice before responding.
    SimultaneousLeaderFollower = 2,
}

/// How the leader is selected for SimultaneousLeaderFollower mode.
#[pyclass(eq, eq_int)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum LeaderSelection {
    /// Leader is randomly selected each game.
    #[default]
    Random = 0,
    /// Player 0 is always the leader.
    AlwaysP0 = 1,
    /// Player 1 is always the leader.
    AlwaysP1 = 2,
}

#[pyclass]
#[derive(Clone, Copy, Debug)]
pub struct RuleConfig {
    /// Start mode for the first move(s)
    #[pyo3(get, set)]
    pub start_mode: StartMode,

    /// How the leader is selected in SimultaneousLeaderFollower mode
    #[pyo3(get, set)]
    pub leader_selection: LeaderSelection,

    /// Landing in own empty pit captures opposite pit's seeds
    #[pyo3(get, set)]
    pub capture_enabled: bool,

    /// Landing in opponent's empty pit forfeits the seed (goes to opponent's store)
    #[pyo3(get, set)]
    pub forfeit_enabled: bool,

    /// Multi-round play with burnt holes (not implemented yet)
    #[pyo3(get, set)]
    pub burnt_holes_enabled: bool,

    /// Capture only allowed after passing through own store at least once
    #[pyo3(get, set)]
    pub capture_requires_loop: bool,
}

#[pymethods]
impl RuleConfig {
    #[new]
    #[pyo3(signature = (
        start_mode=StartMode::Sequential,
        leader_selection=LeaderSelection::Random,
        capture_enabled=true,
        forfeit_enabled=true,
        burnt_holes_enabled=false,
        capture_requires_loop=false
    ))]
    pub fn new(
        start_mode: StartMode,
        leader_selection: LeaderSelection,
        capture_enabled: bool,
        forfeit_enabled: bool,
        burnt_holes_enabled: bool,
        capture_requires_loop: bool,
    ) -> Self {
        RuleConfig {
            start_mode,
            leader_selection,
            capture_enabled,
            forfeit_enabled,
            burnt_holes_enabled,
            capture_requires_loop,
        }
    }

    #[staticmethod]
    pub fn default_rules() -> Self {
        RuleConfig {
            start_mode: StartMode::Sequential,
            leader_selection: LeaderSelection::Random,
            capture_enabled: true,
            forfeit_enabled: true,
            burnt_holes_enabled: false,
            capture_requires_loop: false,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "RuleConfig(start_mode={:?}, leader_selection={:?}, capture={}, forfeit={}, burnt_holes={}, capture_requires_loop={})",
            self.start_mode,
            self.leader_selection,
            self.capture_enabled,
            self.forfeit_enabled,
            self.burnt_holes_enabled,
            self.capture_requires_loop
        )
    }
}

impl Default for RuleConfig {
    fn default() -> Self {
        Self::default_rules()
    }
}
