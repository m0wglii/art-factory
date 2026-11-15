import json
from pathlib import Path

from art_factory.generators import DummyGenerator
from art_factory.llm import DummyLLM
from art_factory.models import GenerationRefused
from art_factory.pipeline import run

RULES = Path(__file__).resolve().parents[1] / "rules"


def test_dummy_lauf_schaerft_nach_und_besteht(tmp_path):
    run_dir = run("Ein Roboter angelt am Bergsee", DummyLLM(), DummyGenerator(), RULES, tmp_path)
    manifest = json.loads((run_dir / "lauf.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "qs_bestanden"
    assert manifest["ergebnis"] == "v2.png"
    assert len(manifest["versuche"]) == 2
    assert len(manifest["prompts"]["edit_versionen"]) == 2
    assert manifest["basis"]["gewaehlt"] == "basis-2.png"
    for name in ("idee.md", "konzepte.json", "basis-1.png", "basis-2.png", "v1.png", "v2.png", "REVIEW.md"):
        assert (run_dir / name).exists()


def test_max_versuche_begrenzt_kosten(tmp_path):
    run_dir = run("Idee", DummyLLM(), DummyGenerator(), RULES, tmp_path, max_versuche=1)
    manifest = json.loads((run_dir / "lauf.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "qs_nicht_bestanden"
    assert manifest["ergebnis"] == "v1.png"
    assert not (run_dir / "v2.png").exists()


def test_ablehnung_wird_protokolliert_nicht_umgangen(tmp_path):
    class Verweigerer(DummyGenerator):
        calls = 0

        def edit(self, image, prompt, out):
            self.calls += 1
            raise GenerationRefused("abgelehnt")

    gen = Verweigerer()
    run_dir = run("Idee", DummyLLM(), gen, RULES, tmp_path)
    manifest = json.loads((run_dir / "lauf.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "abgelehnt"
    assert gen.calls == 1
