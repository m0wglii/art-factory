# Art Factory

Von der Idee zum Bild: Ein Satz wird zu Bildkonzepten entfaltet, ein Agent schreibt die Prompts, erzeugt das Bild, prüft es gegen eine Rubrik und legt das Ergebnis zur Freigabe vor.

Stil: Deko-Malerei vom Flohmarkt, die auf den zweiten Blick ein popkulturelles Element in sich trägt. Regeln siehe `rules/`.

## Stand

Durchstich. Die Pipeline läuft Ende zu Ende im Trockenlauf mit Platzhalterbildern. Die echten Adapter sind angelegt, aber noch nicht gegen die APIs getestet.

| Stufe | Stand |
|---|---|
| 1 Idee | Kommandozeile, Issue-Vorlage vorhanden |
| 2 Entfaltung | implementiert |
| 3 Prompting | implementiert |
| 4 Erzeugung | Dummy getestet, Gemini-Adapter ungetestet |
| 5 QS | implementiert, mit Nachschärf-Schleife |
| 6 Freigabe | `REVIEW.md` je Lauf, GitHub-Anbindung offen |
| 7 Druck | bewusst nicht Teil dieses Stands |

## Schnellstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
art-factory run "Ein kleiner Roboter angelt an einem Bergsee" --dummy
```

Echter Lauf:

```bash
pip install -e ".[api]"
cp .env.example .env   # Schlüssel und Modellkennung eintragen, dann exportieren
art-factory run "Ein kleiner Roboter angelt an einem Bergsee"
```

## Aufbau

```
rules/            Stilregeln, Prompt-Gerüste, QS-Rubrik (vom Agenten gelesen)
src/art_factory/  Pipeline
  stages.py       Entfaltung, Prompting, QS, Nachschärfen
  pipeline.py     Orchestrierung und Lauf-Protokoll
  generators.py   Bildmodell-Adapter (austauschbar)
  llm.py          Sprachmodell-Adapter
runs/             ein Ordner je Lauf
tests/            Trockenlauf-Tests
```

## Ein Lauf

Jeder Lauf erzeugt `runs/<zeit>-<idee>/` mit:

- `idee.md`, `konzepte.json`
- `basis.png`, `v1.png` bis `vN.png`
- `lauf.json`: alle Prompts, alle QS-Bewertungen, Status
- `REVIEW.md`: Vorschlag, QS-Tabelle, Entscheidungsfelder

Der Ordner ist zugleich die Entstehungsdokumentation für Spur V.

## Leitplanken

- **Kostenbremse:** je Lauf höchstens ein Basisbild und `--max-versuche` Bearbeitungen (Standard 3).
- **Spuren:** Ideen mit bekannten Figuren, Marken oder Logos werden zwingend als Spur P geführt und sind nicht verkaufsfähig.
- **Ablehnungen:** Lehnt das Bildmodell eine Anfrage ab, wird das als Status `abgelehnt` protokolliert. Die Pipeline umgeht das nicht.
- **QS:** Das Modell prüft Technik und Einbettung. Ob ein Bild gut ist, entscheidet der Mensch.

## Nächste Schritte

1. Gemini-Adapter mit echtem Schlüssel prüfen
2. Mehrere Basisbild-Varianten erzeugen und per QS die beste wählen
3. GitHub Action: Issue mit Label `idee` startet einen Lauf und öffnet einen Pull Request mit `REVIEW.md`
4. Muster 3 und 4 testen
