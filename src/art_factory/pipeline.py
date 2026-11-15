"""Orchestrierung: Idee rein, Lauf-Ordner mit Bildern und Protokoll raus."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .generators import Generator
from .llm import LLM
from .models import GenerationRefused
from .stages import Rules, make_prompts, refine, review, unfold


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "idee"


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(
    idee: str,
    llm: LLM,
    gen: Generator,
    rules_dir: Path,
    runs_dir: Path,
    konzepte: int = 3,
    max_versuche: int = 3,
    muster: int | None = None,
    spur: str | None = None,
) -> Path:
    """Führt einen Lauf für das erste Konzept aus und gibt den Lauf-Ordner zurück.

    Kostenbremse: höchstens 1 Basisbild + `max_versuche` Bearbeitungen je Lauf.
    """
    rules = Rules.load(rules_dir)
    run_dir = runs_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{_slug(idee)}"
    run_dir.mkdir(parents=True)
    (run_dir / "idee.md").write_text(idee + "\n", encoding="utf-8")

    concepts = unfold(llm, rules, idee, konzepte, muster, spur)
    _write_json(run_dir / "konzepte.json", [c.to_dict() for c in concepts])
    concept = concepts[0]

    prompts = make_prompts(llm, rules, concept)
    manifest: dict = {
        "idee": idee,
        "konzept": concept.to_dict(),
        "generator": gen.name,
        "prompts": {"basis": prompts.basis, "edit_versionen": []},
        "versuche": [],
        "status": "offen",
        "ergebnis": None,
    }

    try:
        basis = gen.generate(prompts.basis, run_dir / "basis.png") if prompts.basis else None
        edit_prompt = prompts.edit
        for nr in range(1, max_versuche + 1):
            manifest["prompts"]["edit_versionen"].append(edit_prompt)
            out = run_dir / f"v{nr}.png"
            if basis is not None:
                gen.edit(basis, edit_prompt, out)
            else:
                gen.generate(edit_prompt, out)
            qa = review(llm, rules, concept, out, basis)
            manifest["versuche"].append({"bild": out.name, "qs": qa.to_dict()})
            if qa.bestanden:
                manifest["status"] = "qs_bestanden"
                manifest["ergebnis"] = out.name
                break
            if nr < max_versuche:
                edit_prompt = refine(llm, rules, edit_prompt, qa)
        else:
            beste = max(manifest["versuche"], key=lambda v: v["qs"]["durchschnitt"])
            manifest["status"] = "qs_nicht_bestanden"
            manifest["ergebnis"] = beste["bild"]
    except GenerationRefused as exc:
        # Ablehnung ist ein Ergebnis, kein Fehler. Kein Umweg, kein erneuter Versuch.
        manifest["status"] = "abgelehnt"
        manifest["hinweis"] = str(exc)

    _write_json(run_dir / "lauf.json", manifest)
    (run_dir / "REVIEW.md").write_text(_review_md(manifest), encoding="utf-8")
    return run_dir


def _review_md(m: dict) -> str:
    k = m["konzept"]
    lines = [
        f"# {k['titel']}",
        "",
        f"- **Idee:** {m['idee']}",
        f"- **Muster:** {k['muster']} · **Spur:** {k['spur']}",
        f"- **Status:** {m['status']}",
        f"- **Generator:** {m['generator']}",
        "",
    ]
    if m.get("hinweis"):
        lines += [f"> {m['hinweis']}", ""]
    if m["ergebnis"]:
        lines += [f"## Vorschlag: {m['ergebnis']}", "", f"![Ergebnis]({m['ergebnis']})", ""]
    if m["versuche"]:
        kriterien = list(m["versuche"][0]["qs"]["scores"])
        lines += ["## QS-Protokoll", "", "| Bild | " + " | ".join(kriterien) + " | Ø | bestanden |"]
        lines += ["|---|" + "---|" * (len(kriterien) + 2)]
        for v in m["versuche"]:
            qs = v["qs"]
            werte = " | ".join(str(qs["scores"][c]) for c in kriterien)
            lines.append(f"| {v['bild']} | {werte} | {qs['durchschnitt']} | {'ja' if qs['bestanden'] else 'nein'} |")
        for v in m["versuche"]:
            if v["qs"]["befunde"]:
                lines += ["", f"**Befunde {v['bild']}:** " + "; ".join(v["qs"]["befunde"])]
    lines += ["", "## Entscheidung", "", "- [ ] Freigeben", "- [ ] Verwerfen", "- [ ] Nacharbeiten mit Hinweis:", ""]
    return "\n".join(lines)
