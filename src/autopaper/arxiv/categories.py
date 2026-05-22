"""Default arXiv category aliases used when no YAML runtime config is supplied."""

from __future__ import annotations

DEFAULT_FIELD_CATEGORIES: dict[str, list[str]] = {
    "ai": ["cs.AI", "cs.LG", "stat.ML"],
    "robotics": ["cs.RO"],
    "cv": ["cs.CV", "eess.IV"],
    "nlp": ["cs.CL"],
    "physics": ["physics.comp-ph", "cond-mat", "quant-ph"],
    "math": ["math.OC", "math.ST", "math.NA"],
    "stat": ["stat.ML", "stat.ME", "stat.AP"],
    "eess": ["eess.IV", "eess.SP", "eess.AS"],
    "q-bio": ["q-bio.QM", "q-bio.GN", "q-bio.MN"],
    "all": ["cs.AI", "cs.LG", "cs.RO", "cs.CV", "cs.CL", "cs.CR", "cs.DC", "cs.DS", "cs.HC", "cs.IR"],
}


def default_field_categories() -> dict[str, list[str]]:
    """Return a copy so direct Python API users can mutate categories safely."""
    return {name: list(categories) for name, categories in DEFAULT_FIELD_CATEGORIES.items()}
