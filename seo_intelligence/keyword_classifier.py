"""
Keyword intent classification.

Classifies each keyword into one of:
    Informational | Commercial | Transactional | Navigational | Local | Question

Uses a rule-based approach (fast, no API required) with optional OpenAI
refinement when OPENAI_API_KEY is set.
"""

import re
from dataclasses import dataclass
from enum import Enum

from seo_intelligence.logger import get_logger

log = get_logger(__name__)


class Intent(str, Enum):
    INFORMATIONAL = "Informational"
    COMMERCIAL = "Commercial"
    TRANSACTIONAL = "Transactional"
    NAVIGATIONAL = "Navigational"
    LOCAL = "Local"
    QUESTION = "Question"


# ── Pattern sets ───────────────────────────────────────────────────────────────

_QUESTION_PATTERNS = re.compile(
    r"\b(who|what|when|where|why|how|which|can|do|does|is|are|was|were|will|"
    r"should|would|could|have|has)\b",
    re.IGNORECASE,
)

_QUESTION_SUFFIXES = re.compile(
    r"\?$|^(tips|guide|tutorial|examples|ideas|ways|steps|reasons|meaning|definition)\b",
    re.IGNORECASE,
)

_TRANSACTIONAL_PATTERNS = re.compile(
    r"\b(buy|purchase|order|shop|hire|get|download|subscribe|sign up|signup|"
    r"register|enroll|book|reserve|pay|checkout|deal|discount|coupon|promo|"
    r"cheap|affordable|low.?cost|free quote|quote|pricing|cost|price|"
    r"package|packages|plan|plans)\b",
    re.IGNORECASE,
)

_COMMERCIAL_PATTERNS = re.compile(
    r"\b(best|top|vs|versus|compare|comparison|review|reviews|alternative|"
    r"alternatives|ranking|rated|recommended|agency|agencies|company|"
    r"companies|service|services|provider|providers)\b",
    re.IGNORECASE,
)

_LOCAL_PATTERNS = re.compile(
    r"\b(uganda|kampala|entebbe|jinja|mbarara|gulu|lira|fort portal|mbale|"
    r"near me|nearby|in uganda|ugandan|local)\b",
    re.IGNORECASE,
)

_NAVIGATIONAL_PATTERNS = re.compile(
    r"\b(login|log in|sign in|official|website|site|homepage|portal|"
    r"isazeni|trophy developers|armgenius|webstar)\b",
    re.IGNORECASE,
)


@dataclass
class ClassificationResult:
    keyword: str
    intent: Intent
    confidence: float  # 0–1
    signals: list[str]


def classify(keyword: str) -> ClassificationResult:
    """
    Classify a keyword's search intent.

    Returns a :class:`ClassificationResult` with the predicted intent,
    a confidence score, and the matched signals.
    """
    kw = keyword.strip().lower()
    signals: list[str] = []

    # Question – highest priority
    if _QUESTION_PATTERNS.search(kw) or _QUESTION_SUFFIXES.search(kw) or kw.endswith("?"):
        signals.append("question_pattern")
        return ClassificationResult(keyword, Intent.QUESTION, 0.90, signals)

    # Navigational
    if _NAVIGATIONAL_PATTERNS.search(kw):
        signals.append("navigational_brand")
        return ClassificationResult(keyword, Intent.NAVIGATIONAL, 0.85, signals)

    # Transactional signals outweigh commercial when both match
    trans_match = _TRANSACTIONAL_PATTERNS.search(kw)
    local_match = _LOCAL_PATTERNS.search(kw)
    commercial_match = _COMMERCIAL_PATTERNS.search(kw)

    if trans_match:
        signals.append(f"transactional:{trans_match.group()}")
        if local_match:
            signals.append(f"local:{local_match.group()}")
            return ClassificationResult(keyword, Intent.LOCAL, 0.88, signals)
        return ClassificationResult(keyword, Intent.TRANSACTIONAL, 0.85, signals)

    if local_match:
        signals.append(f"local:{local_match.group()}")
        return ClassificationResult(keyword, Intent.LOCAL, 0.80, signals)

    if commercial_match:
        signals.append(f"commercial:{commercial_match.group()}")
        return ClassificationResult(keyword, Intent.COMMERCIAL, 0.75, signals)

    # Default to informational
    return ClassificationResult(keyword, Intent.INFORMATIONAL, 0.60, ["default"])


def classify_many(keywords: list[str]) -> list[ClassificationResult]:
    """Classify a list of keywords and return results in the same order."""
    results = []
    for kw in keywords:
        try:
            results.append(classify(kw))
        except Exception as exc:
            log.warning("classify error for '%s': %s", kw, exc)
            results.append(
                ClassificationResult(kw, Intent.INFORMATIONAL, 0.0, ["error"])
            )
    return results
