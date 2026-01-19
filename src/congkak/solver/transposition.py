from dataclasses import dataclass
from enum import IntEnum


class TTFlag(IntEnum):
    EXACT = 0
    LOWER_BOUND = 1  # alpha cutoff
    UPPER_BOUND = 2  # beta cutoff


@dataclass(slots=True)
class TTEntry:
    value: float
    depth: int
    flag: TTFlag
    best_move: int | None


class TranspositionTable:
    """Hash table for storing search results."""

    def __init__(self, max_size: int = 1_000_000):
        self.max_size = max_size
        self.table: dict[int, TTEntry] = {}

    def lookup(self, key: int, depth: int, alpha: float, beta: float) -> tuple[float, bool] | None:
        """Look up a position. Returns (value, is_exact) if usable, None otherwise."""
        entry = self.table.get(key)
        if entry is None or entry.depth < depth:
            return None

        if entry.flag == TTFlag.EXACT:
            return entry.value, True
        if entry.flag == TTFlag.LOWER_BOUND and entry.value >= beta:
            return entry.value, False
        if entry.flag == TTFlag.UPPER_BOUND and entry.value <= alpha:
            return entry.value, False

        return None

    def get_best_move(self, key: int) -> int | None:
        """Get cached best move for move ordering."""
        entry = self.table.get(key)
        return entry.best_move if entry else None

    def store(
        self, key: int, value: float, depth: int, flag: TTFlag, best_move: int | None
    ) -> None:
        """Store a position."""
        # simple replacement: always replace if same or greater depth
        existing = self.table.get(key)
        if existing is None or existing.depth <= depth:
            # evict if at capacity (simple random eviction)
            if len(self.table) >= self.max_size and key not in self.table:
                # remove arbitrary entry
                self.table.pop(next(iter(self.table)))
            self.table[key] = TTEntry(value, depth, flag, best_move)

    def clear(self) -> None:
        self.table.clear()

    def __len__(self) -> int:
        return len(self.table)
