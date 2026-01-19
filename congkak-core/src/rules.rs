use pyo3::prelude::*;

#[pyclass]
#[derive(Clone, Copy, Debug)]
pub struct RuleConfig {
    /// Both players select starting pit simultaneously for first move
    #[pyo3(get, set)]
    pub simultaneous_start: bool,

    /// Landing in own empty pit captures opposite pit's seeds
    #[pyo3(get, set)]
    pub capture_enabled: bool,

    /// Landing in opponent's empty pit forfeits the seed (goes to opponent's store)
    #[pyo3(get, set)]
    pub forfeit_enabled: bool,

    /// Multi-round play with burnt holes (not implemented yet)
    #[pyo3(get, set)]
    pub burnt_holes_enabled: bool,
}

#[pymethods]
impl RuleConfig {
    #[new]
    #[pyo3(signature = (simultaneous_start=false, capture_enabled=true, forfeit_enabled=true, burnt_holes_enabled=false))]
    pub fn new(
        simultaneous_start: bool,
        capture_enabled: bool,
        forfeit_enabled: bool,
        burnt_holes_enabled: bool,
    ) -> Self {
        RuleConfig {
            simultaneous_start,
            capture_enabled,
            forfeit_enabled,
            burnt_holes_enabled,
        }
    }

    #[staticmethod]
    pub fn default_rules() -> Self {
        RuleConfig {
            simultaneous_start: false,
            capture_enabled: true,
            forfeit_enabled: true,
            burnt_holes_enabled: false,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "RuleConfig(simultaneous_start={}, capture={}, forfeit={}, burnt_holes={})",
            self.simultaneous_start,
            self.capture_enabled,
            self.forfeit_enabled,
            self.burnt_holes_enabled
        )
    }
}

impl Default for RuleConfig {
    fn default() -> Self {
        Self::default_rules()
    }
}
