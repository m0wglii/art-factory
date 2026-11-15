"""Kommandozeile: art-factory run "Idee in einem Satz"."""
from __future__ import annotations

import argparse
from pathlib import Path

from .generators import get_generator
from .llm import AnthropicLLM, DummyLLM
from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="art-factory")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="Eine Idee durch die Pipeline schicken")
    p.add_argument("idee")
    p.add_argument("--dummy", action="store_true", help="Trockenlauf ohne API-Aufrufe")
    p.add_argument("--generator", default="gemini", choices=["gemini", "dummy"])
    p.add_argument("--muster", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--spur", choices=["P", "V"])
    p.add_argument("--konzepte", type=int, default=3)
    p.add_argument("--max-versuche", type=int, default=3)
    p.add_argument("--rules", type=Path, default=Path("rules"))
    p.add_argument("--runs", type=Path, default=Path("runs"))
    args = parser.parse_args(argv)

    llm = DummyLLM() if args.dummy else AnthropicLLM()
    gen = get_generator("dummy" if args.dummy else args.generator)
    run_dir = run(
        args.idee,
        llm,
        gen,
        rules_dir=args.rules,
        runs_dir=args.runs,
        konzepte=args.konzepte,
        max_versuche=args.max_versuche,
        muster=args.muster,
        spur=args.spur,
    )
    print(f"Lauf abgeschlossen: {run_dir}")
    print(f"Review: {run_dir / 'REVIEW.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
