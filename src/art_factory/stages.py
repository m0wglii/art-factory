"""Die Stufen der Pipeline: Entfaltung, Prompting, QS, Nachschärfen."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from .llm import LLM
from .models import Concept, Prompts, QAResult


@dataclass
class Rules:
    stil: str
    prompts: dict
    rubrik: dict

    @classmethod
    def load(cls, rules_dir: Path) -> "Rules":
        return cls(
            stil=(rules_dir / "stil.md").read_text(encoding="utf-8"),
            prompts=yaml.safe_load((rules_dir / "prompts.yaml").read_text(encoding="utf-8")),
            rubrik=yaml.safe_load((rules_dir / "qs-rubrik.yaml").read_text(encoding="utf-8")),
        )


def unfold(
    llm: LLM, rules: Rules, idee: str, anzahl: int = 3, muster: int | None = None, spur: str | None = None
) -> list[Concept]:
    """Stufe 2: aus einem Satz mehrere Bildkonzepte machen."""
    system = (
        "STUFE:ENTFALTUNG\nDu entwickelst Bildkonzepte nach diesen Stilregeln:\n\n"
        f"{rules.stil}\n\n"
        "Gib ein JSON-Objekt {\"konzepte\": [...]} zurück. Jedes Konzept hat die Felder "
        "muster (1-4), spur (P oder V), titel, basis_szene, element, platzierung, begruendung. "
        "Enthält die Idee eine bekannte Figur, Marke oder ein Logo, ist die Spur zwingend P, "
        "auch wenn V gewünscht wurde. Bevorzuge Muster mit hoher Priorität."
    )
    user = f"Idee: {idee}\nAnzahl Konzepte: {anzahl}"
    if muster:
        user += f"\nGewünschtes Muster: {muster}"
    if spur:
        user += f"\nGewünschte Spur: {spur}"
    data = llm.json(system, user)
    return [Concept.from_dict(c) for c in data["konzepte"]]


def make_prompts(llm: LLM, rules: Rules, concept: Concept) -> Prompts:
    """Stufe 3: Konzept in die Prompt-Gerüste füllen."""
    spec = rules.prompts["muster"][concept.muster]
    system = (
        "STUFE:PROMPTING\nDu schreibst englische Prompts für ein Bildmodell.\n\n"
        f"Gerüst Basisbild:\n{rules.prompts['basis']}\n\n"
        f"Gerüst Muster {concept.muster} ({spec['name']}):\n{spec['edit']}\n\n"
        "Regeln:\n- " + "\n- ".join(rules.prompts["regeln"]) + "\n\n"
        "Fülle alle Platzhalter. Gib {\"basis\": ..., \"edit\": ...} zurück. "
        "Bei einstufigen Mustern ist basis null."
    )
    data = llm.json(system, json.dumps(concept.to_dict(), ensure_ascii=False))
    basis = data.get("basis") if spec.get("zweistufig", True) else None
    return Prompts(basis=basis, edit=data["edit"])


def review(llm: LLM, rules: Rules, concept: Concept, bild: Path, basis: Path | None) -> QAResult:
    """Stufe 5: Bild gegen die Rubrik prüfen."""
    kriterien = rules.rubrik["kriterien"]
    fragen = "\n".join(f"- {key}: {val['frage']}" for key, val in kriterien.items())
    system = (
        "STUFE:QS\nDu prüfst ein erzeugtes Bild streng gegen diese Kriterien, je 1 bis 5:\n"
        f"{fragen}\n\n"
        "Bewerte nur, was du siehst. Geschmack und Witz bewertest du nicht. "
        "Gib {\"scores\": {kriterium: zahl}, \"befunde\": [kurze Mängelbeschreibungen]} zurück."
    )
    user = f"Konzept: {json.dumps(concept.to_dict(), ensure_ascii=False)}\n"
    images = [bild]
    if basis is not None:
        user += "Bild 1 ist das Basisbild, Bild 2 das Ergebnis."
        images = [basis, bild]
    data = llm.json(system, user, images=images)
    scores = {key: int(data["scores"].get(key, 1)) for key in kriterien}
    schnitt = sum(scores.values()) / len(scores)
    bestanden = min(scores.values()) >= rules.rubrik["mindestwert"] and schnitt >= rules.rubrik["durchschnitt"]
    return QAResult(scores=scores, befunde=list(data.get("befunde", [])), bestanden=bestanden, durchschnitt=round(schnitt, 2))


def refine(llm: LLM, rules: Rules, edit_prompt: str, qa: QAResult) -> str:
    """Edit-Prompt anhand der QS-Befunde nachschärfen."""
    tabelle = "\n".join(f"- {z['befund']}: {z['zusatz']}" for z in rules.prompts["nachschaerfen"])
    system = (
        "STUFE:NACHSCHAERFEN\nDu verbesserst einen Edit-Prompt anhand von QS-Befunden. "
        f"Nutze diese Tabelle:\n{tabelle}\n\n"
        "Ändere nur, was die Befunde verlangen. Gib {\"edit\": ...} zurück."
    )
    user = f"Bisheriger Prompt:\n{edit_prompt}\n\nBefunde:\n" + "\n".join(qa.befunde)
    user += f"\n\nBewertung: {json.dumps(qa.scores)}"
    return llm.json(system, user)["edit"]


def choose_base(llm: LLM, rules: Rules, concept: Concept, kandidaten: list[Path]) -> tuple[int, str]:
    """Wählt aus mehreren Basisbildern das beste. Gibt (Index ab 0, Begründung) zurück."""
    system = (
        "STUFE:BASISWAHL\nDu wählst das Basisbild, das am besten zu diesen Stilregeln passt und "
        "an der vorgesehenen Stelle eine ruhige Fläche für das Element bietet:\n\n"
        f"{rules.stil}\n\n"
        "Gib {\"wahl\": Bildnummer ab 1, \"grund\": kurzer Satz} zurück."
    )
    user = f"Konzept: {json.dumps(concept.to_dict(), ensure_ascii=False)}\nBilder in Reihenfolge 1 bis {len(kandidaten)}."
    data = llm.json(system, user, images=kandidaten)
    wahl = min(max(int(data.get("wahl", 1)), 1), len(kandidaten)) - 1
    return wahl, str(data.get("grund", ""))
