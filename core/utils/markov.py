from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import random
from typing import Dict, List, Tuple, Iterable, Optional, Set

# Special tokens that won't collide with normal text.
_START = "\u0002"
_END = "\u0003"

@dataclass
class ModelEntry:
    """Precomputed sampling tables for a single prefix."""
    symbols: List[str]       # Possible next chars
    weights: List[int]       # Corresponding counts (weights)
    total: int               # Total weight for quick checks


class MarkovNameGenerator:
    """
    Character-level Markov chain generator for names/words.

    - order (int): The n-gram order (token size). For bigrams set to 2.
    - seed (Optional[int|str]): Base seed for deterministic RNG.
    - normalize_case (bool): If True, trains on lowercase and capitalizes outputs.
    """

    def __init__(
        self,
        order: int = 2,
        seed: Optional[object] = None,
        normalize_case: bool = True,
    ):
        if order < 2:
            raise ValueError("order must be >= 2 (e.g., 2 for bigrams, 3 for trigrams)")
        self.order = order
        self.normalize_case = normalize_case

        # Build a dedicated RNG, optionally seeded deterministically.
        self.rng = random.Random(self._mix_seed(seed))

        # Model: prefix (tuple of length order-1) -> ModelEntry
        self._model: Dict[Tuple[str, ...], ModelEntry] = {}

        # Keep the training set for de-duplication under avoid_training=True
        self._training_words: Set[str] = set()

    @staticmethod
    def _mix_seed(seed: Optional[object]) -> Optional[int]:
        """
        Convert seed deterministically into an integer suitable for random.Random.
        Returns None if both are None (non-deterministic RNG).
        """
        if seed is None:
            return None  # system entropy
        s = f"{seed!r}".encode("utf-8")
        digest = hashlib.sha256(s).hexdigest()
        return int(digest, 16)  # big integer seed

    @staticmethod
    def _prepare_word(word: str, normalize_case: bool) -> str:
        """Apply case normalization if requested."""
        return word.lower() if normalize_case else word

    def fit(self, words: Iterable[str]) -> None:
        """
        Train the model from a list/iterable of discrete words.
        """
        counts: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)
        self._training_words.clear()

        for raw in words:
            if not raw:
                continue
            self._training_words.add(raw)
            w = self._prepare_word(raw, self.normalize_case)

            # Pad with start tokens and end token: e.g., for order=3: ^ ^ w $
            padded = (_START * (self.order - 1)) + w + _END

            # Build counts of next-char given prefix of length order-1
            for i in range(0, len(padded) - (self.order - 1)):
                prefix = tuple(padded[i : i + (self.order - 1)])
                next_char_idx = i + (self.order - 1)
                next_char = padded[next_char_idx]
                counts[prefix][next_char] += 1

        # Precompute sampling tables for efficiency and determinism
        self._model.clear()
        for prefix, counter in counts.items():
            # Sort symbols for reproducibility across Python runs
            symbols = sorted(counter.keys())
            weights = [counter[s] for s in symbols]
            total = sum(weights)
            self._model[prefix] = ModelEntry(symbols, weights, total)

        # Basic sanity: ensure we can start generation
        start_prefix = tuple(_START for _ in range(self.order - 1))
        if start_prefix not in self._model:
            raise RuntimeError(
                "Model training failed: missing start prefix. "
                "Ensure the input contains at least one non-empty word."
            )

    def _sample_next(self, prefix: Tuple[str, ...]) -> Optional[str]:
        """
        Sample the next character given a prefix using the model.
        Returns None if the prefix is unseen (should be rare).
        """
        entry = self._model.get(prefix)
        if not entry or entry.total == 0:
            return None
        # Deterministic RNG thanks to self.rng
        return self.rng.choices(entry.symbols, weights=entry.weights, k=1)[0]

    def generate(
        self,
        max_len: int = 30,
        min_len: int = 1,
        avoid_training: bool = True,
        max_attempts: int = 100,
    ) -> Optional[str]:
        """
        Generate a single name/word.

        - max_len: hard cap on characters (excluding start/end markers).
        - min_len: minimum characters required (excluding markers).
        - avoid_training: avoid returning any exact training word.
        - max_attempts: attempts before giving up if avoid_training is True.
        """
        start_prefix = tuple(_START for _ in range(self.order - 1))

        for _ in range(max_attempts):
            prefix = start_prefix
            out_chars: List[str] = []

            # Sample until end token or max_len reached
            while len(out_chars) < max_len:
                nxt = self._sample_next(prefix)
                if nxt is None:
                    # Fallback: terminate early if model lacks this prefix
                    break
                if nxt == _END:
                    break
                out_chars.append(nxt)
                # Slide the prefix window forward
                prefix = (*prefix[1:], nxt)

            # Enforce length constraints and avoid training words if requested
            candidate = "".join(out_chars)
            if len(candidate) < min_len:
                continue
            if avoid_training:
                # Compare with normalized training words if normalize_case=True
                comp = candidate if not self.normalize_case else candidate.lower()
                # If training words were not normalized, compare raw data
                # but we trained on normalized, so check case-insensitive match
                if any(self._prepare_word(w, self.normalize_case) == comp for w in self._training_words):
                    continue

            # Capitalize nicely if we normalized case during training
            if self.normalize_case and candidate:
                candidate = candidate[0].upper() + candidate[1:]

            return candidate

        return None  # Could not produce a valid candidate under constraints

    def generate_many(
        self,
        k: int,
        unique: bool = True,
        **kwargs,
    ) -> List[str]:
        """
        Generate multiple names/words.

        - k: number of items to produce.
        - unique: if True, deduplicate generated outputs.
        - kwargs: forwarded to `generate` (e.g., max_len, min_len, avoid_training).
        """
        results: List[str] = []
        seen: Set[str] = set()
        attempts = 0
        target = k

        while len(results) < target and attempts < k * 50:
            attempts += 1
            item = self.generate(**kwargs)
            if item is None:
                continue
            if unique:
                if item in seen:
                    continue
                seen.add(item)
            results.append(item)
        return results


if __name__ == "__main__":
    from corpus import CORPUS

    corp = CORPUS['towns']
    seed = 'dvw4fg23f'
    count = 25

    gen = MarkovNameGenerator(order=3, seed=seed, normalize_case=True)
    gen.fit(corp)
    values = gen.generate_many(k=count, max_len=32, min_len=6, avoid_training=True)
    for v in values:
        print(v.title())