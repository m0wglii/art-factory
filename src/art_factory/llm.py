"""Sprachmodell-Anbindung. Jede Stufe ruft `json()` auf und erwartet ein JSON-Objekt."""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Protocol


class LLM(Protocol):
    def json(self, system: str, user: str, images: list[Path] | None = None) -> dict: ...


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Keine JSON-Antwort erhalten: {text[:200]}")
    return json.loads(match.group(0))


class AnthropicLLM:
    """Claude über die Anthropic-API. Benötigt ANTHROPIC_API_KEY."""

    def __init__(self, model: str | None = None, max_tokens: int = 2000):
        import anthropic  # erst hier, damit der Dummy-Modus ohne Paket läuft

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("ART_FACTORY_LLM_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens

    def json(self, system: str, user: str, images: list[Path] | None = None) -> dict:
        content: list[dict] = []
        for path in images or []:
            data = base64.standard_b64encode(Path(path).read_bytes()).decode()
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": data},
                }
            )
        content.append({"type": "text", "text": user})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system + "\n\nAntworte ausschließlich mit einem JSON-Objekt.",
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return _extract_json(text)


class DummyLLM:
    """Feste Antworten für Tests und Trockenläufe ohne API-Schlüssel."""

    def __init__(self):
        self.qa_calls = 0

    def json(self, system: str, user: str, images: list[Path] | None = None) -> dict:
        if "STUFE:ENTFALTUNG" in system:
            return {
                "konzepte": [
                    {
                        "muster": 1,
                        "spur": "V",
                        "titel": "Stille Wasser, altes Blech",
                        "basis_szene": "Bergsee mit Tannen und Schneegipfel bei Sonnenuntergang",
                        "element": "kleiner rostiger Blechroboter, der angelt",
                        "platzierung": "unten links am Ufer, etwa 8 % der Bildhöhe",
                        "begruendung": "Dummy-Konzept",
                    }
                ]
            }
        if "STUFE:PROMPTING" in system:
            return {
                "basis": "Oil painting on canvas ... a mountain lake ... Aspect ratio 4:3.",
                "edit": "Edit this painting: add a small rusty tin robot seen from behind ...",
            }
        if "STUFE:QS" in system:
            self.qa_calls += 1
            wert = 2 if self.qa_calls == 1 else 5
            return {
                "scores": {
                    "erster_blick": 5,
                    "zweiter_blick": 4,
                    "duktus": wert,
                    "licht": wert,
                    "palette": 4,
                    "basis_erhalten": 5,
                    "technik": 5,
                },
                "befunde": [] if wert == 5 else ["Element wirkt aufgeklebt, zu glatt oder glänzend"],
            }
        if "STUFE:BASISWAHL" in system:
            return {"wahl": 2, "grund": "ruhigere Fläche für das Element"}
        if "STUFE:NACHSCHAERFEN" in system:
            return {"edit": "Edit this painting (nachgeschärft): ... matte surface ..."}
        raise ValueError("Unbekannte Stufe im Dummy-LLM")
