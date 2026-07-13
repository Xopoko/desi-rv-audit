from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


FOLD_HASH_ALGORITHM = "blake2b-64-v1"
_PERSONALIZATION = b"desi-rv-fold-v1"


def stable_hash64(value: object) -> int:
    """Return a platform-independent 64-bit hash for fold assignment and seeds."""
    canonical = "<NA>" if pd.isna(value) else str(value).strip()
    digest = hashlib.blake2b(
        canonical.encode("utf-8"),
        digest_size=8,
        person=_PERSONALIZATION,
    ).digest()
    return int.from_bytes(digest, byteorder="little", signed=False)


def stable_hash_mod(values: pd.Series, modulo: int) -> np.ndarray:
    if modulo < 1:
        raise ValueError("modulo must be positive")
    canonical = values.astype("string").fillna("<NA>")
    codes, unique_values = pd.factorize(canonical, sort=False)
    unique_hashes = np.fromiter(
        (stable_hash64(value) for value in unique_values),
        dtype=np.uint64,
        count=len(unique_values),
    )
    return (unique_hashes[codes] % np.uint64(modulo)).astype(np.int64)


def stable_seed(label: str) -> int:
    return stable_hash64(label) % (2**32)
