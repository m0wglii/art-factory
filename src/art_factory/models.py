"""Datenstrukturen der Pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Concept:
    muster: int
    spur: str  # "P" oder "V"
    titel: str
    basis_szene: str
    element: str
    platzierung: str
    begruendung: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Concept":
        return cls(
            muster=int(d["muster"]),
            spur=str(d["spur"]).upper(),
            titel=d["titel"],
            basis_szene=d["basis_szene"],
            element=d["element"],
            platzierung=d.get("platzierung", ""),
            begruendung=d.get("begruendung", ""),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Prompts:
    basis: str | None  # None bei einstufigen Mustern
    edit: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QAResult:
    scores: dict[str, int]
    befunde: list[str] = field(default_factory=list)
    bestanden: bool = False
    durchschnitt: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class GenerationRefused(Exception):
    """Das Bildmodell hat die Anfrage abgelehnt oder kein Bild geliefert."""
