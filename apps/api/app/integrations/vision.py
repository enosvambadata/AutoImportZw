"""Vehicle-photo damage analysis providers.

The MVP ships a deterministic **mock** adapter (used whenever no Anthropic API key is configured)
and a **Claude vision** adapter that uses Claude as an intelligent advisor to assess *visible*
damage in uploaded photos and tailor its notes to the dealership's own details.

This is an interim capability until a dedicated vehicle-damage-detection data connector is
licensed. Every result is labelled with its ``analysis_source`` and carries a disclaimer: it
assesses visible damage only from photos and never replaces a physical/mechanical inspection.
"""

from __future__ import annotations

import json
from typing import Any

MOCK_SOURCE = "MOCK_ADAPTER"
CLAUDE_SOURCE = "CLAUDE_VISION"

DISCLAIMER = (
    "Assessment of visible damage from photos only. Not a physical or mechanical inspection; "
    "hidden or underbody damage may not be visible. Treat repair figures as rough estimates and "
    "verify in person before bidding."
)

# JSON Schema for structured output (kept within the supported subset: no numeric/length bounds).
DAMAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_condition": {"type": "string", "enum": ["EXCELLENT", "GOOD", "FAIR", "POOR"]},
        "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "summary": {"type": "string"},
        "damage_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "panel": {"type": "string"},
                    "damage_type": {"type": "string"},
                    "severity": {"type": "string", "enum": ["MINOR", "MODERATE", "SEVERE"]},
                    "estimated_repair_min": {"type": "number"},
                    "estimated_repair_max": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["panel", "damage_type", "severity", "estimated_repair_min",
                             "estimated_repair_max", "notes"],
            },
        },
        "suggested_cost_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string",
                                 "enum": ["BODYWORK", "MECHANICAL", "TYRES", "GLASS",
                                          "VALETING", "OTHER"]},
                    "estimated_amount": {"type": "number"},
                    "minimum_amount": {"type": "number"},
                    "maximum_amount": {"type": "number"},
                },
                "required": ["name", "category", "estimated_amount", "minimum_amount",
                             "maximum_amount"],
            },
        },
        "recommended_checks": {"type": "array", "items": {"type": "string"}},
        "advisor_notes": {"type": "string"},
    },
    "required": ["overall_condition", "confidence", "summary", "damage_items",
                 "suggested_cost_items", "recommended_checks", "advisor_notes"],
}

SYSTEM_PROMPT = (
    "You are an experienced UK used-car buyer and vehicle appraiser advising an independent motor "
    "dealer at auction. You assess ONLY visible damage in the supplied photographs. Be specific and "
    "conservative. Give rough GBP repair-cost ranges typical of UK trade repairers. Never claim to "
    "detect mechanical or hidden faults you cannot see; instead list them under recommended_checks. "
    "Tailor advisor_notes to the dealer's target profit and the vehicle provided. Do not guarantee "
    "profit or condition. Return only the requested structured fields."
)


def _context_prompt(context: dict[str, Any]) -> str:
    v = context or {}
    lines = ["Assess the visible condition and damage of this vehicle from the photos."]
    desc = " ".join(str(v.get(k)) for k in ("make", "model", "derivative") if v.get(k))
    if desc:
        lines.append(f"Vehicle: {desc}.")
    if v.get("model_year"):
        lines.append(f"Year: {v['model_year']}.")
    if v.get("mileage"):
        lines.append(f"Mileage: {v['mileage']}.")
    if v.get("dealership_name"):
        lines.append(f"Dealer: {v['dealership_name']}.")
    if v.get("target_profit"):
        lines.append(f"The dealer's target profit is £{v['target_profit']}; keep repair costs in "
                     "proportion so the deal can still work.")
    if v.get("notes"):
        lines.append(f"Dealer notes: {v['notes']}")
    lines.append("Suggest cost items the dealer should budget for the visible work only.")
    return " ".join(lines)


class MockDamageAnalysisProvider:
    """Deterministic, offline stub used when no Claude API key is configured."""

    name = "mock-damage"

    def analyse(self, images: list[tuple[str, str]], context: dict[str, Any]) -> dict[str, Any]:
        make = (context or {}).get("make", "the vehicle")
        n = max(1, len(images))
        return {
            "analysis_source": MOCK_SOURCE,
            "images_analysed": len(images),
            "disclaimer": DISCLAIMER,
            "result": {
                "overall_condition": "FAIR",
                "confidence": "LOW",
                "summary": (f"Demonstration assessment for {make}. This is placeholder output from a "
                            "mock adapter — configure a Claude API key to analyse real photos."),
                "damage_items": [
                    {"panel": "Front bumper", "damage_type": "Scuffs / scratches",
                     "severity": "MINOR", "estimated_repair_min": 120, "estimated_repair_max": 260,
                     "notes": "Cosmetic; smart repair likely sufficient (mock)."},
                    {"panel": "Alloy wheel", "damage_type": "Kerbing", "severity": "MINOR",
                     "estimated_repair_min": 60, "estimated_repair_max": 140,
                     "notes": "Refurbish one corner (mock)."},
                ][:n + 1],
                "suggested_cost_items": [
                    {"name": "Front bumper smart repair (estimate)", "category": "BODYWORK",
                     "estimated_amount": 180, "minimum_amount": 120, "maximum_amount": 260},
                    {"name": "Alloy refurbishment (estimate)", "category": "BODYWORK",
                     "estimated_amount": 90, "minimum_amount": 60, "maximum_amount": 140},
                ],
                "recommended_checks": [
                    "Physically inspect panel gaps and paint depth for prior repairs.",
                    "Start the engine and check for warning lights and unusual noises.",
                    "Confirm no structural or underbody damage.",
                ],
                "advisor_notes": ("Placeholder advisor note. With a real analysis, guidance here is "
                                  "tailored to your target profit and the specific vehicle."),
            },
        }


class ClaudeDamageAnalysisProvider:
    """Claude vision adapter — the intelligent advisor. Requires an Anthropic API key."""

    name = "claude-damage"

    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        self._api_key = api_key
        self._model = model

    def analyse(self, images: list[tuple[str, str]], context: dict[str, Any]) -> dict[str, Any]:
        # Lazy import so the app runs without the anthropic package unless this path is used.
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        content: list[dict[str, Any]] = [
            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}
            for mt, data in images
        ]
        content.append({"type": "text", "text": _context_prompt(context)})

        message = client.messages.create(
            model=self._model,
            max_tokens=3000,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": DAMAGE_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in message.content if getattr(b, "type", None) == "text")
        result = json.loads(text)
        return {
            "analysis_source": CLAUDE_SOURCE,
            "images_analysed": len(images),
            "disclaimer": DISCLAIMER,
            "result": result,
        }
