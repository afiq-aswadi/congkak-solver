pub mod board;
pub mod moves;
pub mod rules;
pub mod simulation;

use pyo3::prelude::*;

#[pymodule]
fn congkak_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // board types
    m.add_class::<board::BoardState>()?;

    // rules
    m.add_class::<rules::RuleConfig>()?;

    // move types and functions
    m.add_class::<moves::MoveResult>()?;
    m.add_function(wrap_pyfunction!(moves::apply_move, m)?)?;
    m.add_function(wrap_pyfunction!(moves::get_legal_moves, m)?)?;
    m.add_function(wrap_pyfunction!(moves::is_terminal, m)?)?;
    m.add_function(wrap_pyfunction!(moves::get_winner, m)?)?;
    m.add_function(wrap_pyfunction!(moves::get_final_scores, m)?)?;

    // simulation functions
    m.add_function(wrap_pyfunction!(simulation::random_playout, m)?)?;
    m.add_function(wrap_pyfunction!(simulation::batch_random_playouts, m)?)?;
    m.add_function(wrap_pyfunction!(simulation::perft, m)?)?;

    Ok(())
}
