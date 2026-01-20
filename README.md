# Congkak

A [Congkak](https://en.wikipedia.org/wiki/Congkak) game with a minimax AI solver.

## Build

Requires [uv](https://docs.astral.sh/uv/) and Rust toolchain.

```bash
uv sync
maturin develop --release
```

## Usage

CLI provided via [tyro](https://github.com/brentyi/tyro):

```bash
uv run python -m congkak.cli --help
```

Play against AI (default):
```bash
uv run python -m congkak.cli
```

AI vs AI:
```bash
uv run python -m congkak.cli --p0 ai --p1 ai --animation-delay 100
```

Terminal mode:
```bash
uv run python -m congkak.cli --no-gui
```

Custom initial state:
```bash
uv run python -m congkak.cli \
    --p0-pits "1,2,3,4,5,6,7" \
    --p1-pits "7,6,5,4,3,2,1" \
    --starting-player 1
```
