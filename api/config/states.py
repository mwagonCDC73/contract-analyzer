"""
Single source of truth for supported states.

To add a new state (e.g. Arizona), add one entry to SUPPORTED_STATES.
Everything else — API responses, AI prompts, frontend dropdowns — derives from it.
"""

from typing import Dict, List, Optional

SUPPORTED_STATES: Dict[str, dict] = {
    "CA": {
        "code": "CA",
        "name": "California",
        "label": "CA - California",
        "context_note": (
            "This is a wall & ceiling / drywall subcontractor contract review "
            "for California Drywall Co. operating in California. "
            "Focus on risks relevant to a specialty subcontractor in California."
        ),
        "legal_checklist": [
            "Civil Code §8800 (prompt payment requirements)",
            "Civil Code §2782 (indemnity limitations)",
            "Mechanics lien rights (Civil Code §8000 et seq.)",
            "CSLB licensing requirements",
            "Prevailing wage requirements (Labor Code §1720 et seq.)",
            "Stop notice rights (Civil Code §8500 et seq.)",
            "Retention limits (Civil Code §8814)",
            "Cal-OSHA safety requirements",
        ],
    },
    "NV": {
        "code": "NV",
        "name": "Nevada",
        "label": "NV - Nevada",
        "context_note": (
            "This is a wall & ceiling / drywall subcontractor contract review "
            "for California Drywall Co. operating in Nevada. "
            "Focus on risks relevant to a specialty subcontractor in Nevada."
        ),
        "legal_checklist": [
            "NRS 624.609-630 (prompt payment requirements)",
            "NRS 108 (mechanics lien rights)",
            "NRS 624 (contractor licensing requirements)",
            "NRS 338 (prevailing wage on public works)",
            "NRS 338.515 (retainage limitations)",
            "Indemnity provisions under Nevada law",
            "Bonding requirements",
            "Nevada OSHA safety requirements",
        ],
    },
}


def get_state_config(code: str) -> Optional[dict]:
    """Return config for a state code, or None if unsupported."""
    return SUPPORTED_STATES.get(code)


def get_state_codes() -> List[str]:
    """Return list of supported state codes."""
    return list(SUPPORTED_STATES.keys())


def get_states_for_api() -> List[dict]:
    """Return list of states formatted for the frontend API."""
    return [
        {"code": s["code"], "name": s["name"], "label": s["label"]}
        for s in SUPPORTED_STATES.values()
    ]
