"""Einstieg für die GitHub Action: liest ein Ideen-Issue und startet einen Lauf.

Der Issue-Text kommt über die Umgebungsvariable ISSUE_BODY, nie über die Shell.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .generators import get_generator
from .llm import AnthropicLLM, DummyLLM
from .pipeline import run


def parse_issue(body: str) -> dict:
    """Zerlegt den Text der Issue-Vorlage in Idee, Muster und Spur."""
    sections: dict[str, str] = {}
    current = None
    for line in (body or "").splitlines():
        heading = re.match(r"^###\s+(.*)$", line.strip())
        if heading:
            current = heading.group(1).strip().lower()
            sections[current] = ""
        elif current is not None:
            sections[current] += line + "\n"

    def find(prefix: str) -> str:
        for key, value in sections.items():
            if key.startswith(prefix):
                return value.strip()
        return ""

    idee = find("idee") or (body or "").strip()
    muster_match = re.match(r"^([1-4])\b", find("muster"))
    spur_match = re.match(r"^([PV])\b", find("spur"))
    return {
        "idee": " ".join(idee.split()),
        "muster": int(muster_match.group(1)) if muster_match else None,
        "spur": spur_match.group(1) if spur_match else None,
    }


def main() -> int:
    parsed = parse_issue(os.environ.get("ISSUE_BODY", ""))
    if not parsed["idee"] or parsed["idee"] == "_No response_":
        print("Keine Idee im Issue gefunden.", file=sys.stderr)
        return 1

    dummy = os.environ.get("ART_FACTORY_DUMMY") == "1"
    llm = DummyLLM() if dummy else AnthropicLLM()
    gen = get_generator("dummy" if dummy else os.environ.get("ART_FACTORY_GENERATOR", "gemini"))
    run_dir = run(
        parsed["idee"],
        llm,
        gen,
        rules_dir=Path("rules"),
        runs_dir=Path("runs"),
        muster=parsed["muster"],
        spur=parsed["spur"],
    )
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"run_dir={run_dir.as_posix()}\n")
    print(f"Lauf abgeschlossen: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
