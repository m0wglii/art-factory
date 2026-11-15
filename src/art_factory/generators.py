"""Bildmodell-Adapter. Die Pipeline kennt nur `generate` und `edit`."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .models import GenerationRefused


class Generator(Protocol):
    name: str

    def generate(self, prompt: str, out: Path) -> Path: ...

    def edit(self, image: Path, prompt: str, out: Path) -> Path: ...


class DummyGenerator:
    """Erzeugt Platzhalterbilder. Für Tests und Trockenläufe."""

    name = "dummy"

    def _render(self, text: str, out: Path, color: tuple[int, int, int]) -> Path:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (1024, 768), color)
        ImageDraw.Draw(img).text((24, 24), text[:400], fill=(255, 255, 255))
        img.save(out)
        return out

    def generate(self, prompt: str, out: Path) -> Path:
        return self._render("BASIS\n" + prompt, out, (70, 110, 120))

    def edit(self, image: Path, prompt: str, out: Path) -> Path:
        return self._render("EDIT\n" + prompt, out, (120, 90, 70))


class GeminiGenerator:
    """Google Gemini über das Paket `google-genai`.

    UNGETESTET: In der Entwicklungsumgebung gab es keinen API-Schlüssel. Vor dem
    ersten echten Lauf gegen die aktuelle Dokumentation prüfen.

    Benötigt GEMINI_API_KEY und GEMINI_IMAGE_MODEL (Modellkennung laut Google-Doku,
    bewusst ohne Vorgabe, weil sich die Kennungen häufig ändern).
    """

    name = "gemini"

    def __init__(self, model: str | None = None):
        from google import genai

        self.client = genai.Client()
        self.model = model or os.environ.get("GEMINI_IMAGE_MODEL")
        if not self.model:
            raise RuntimeError("GEMINI_IMAGE_MODEL ist nicht gesetzt.")

    def _save_first_image(self, response, out: Path) -> Path:
        for candidate in getattr(response, "candidates", None) or []:
            parts = getattr(getattr(candidate, "content", None), "parts", None) or []
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is not None and inline.data:
                    out.write_bytes(inline.data)
                    return out
        raise GenerationRefused("Das Bildmodell hat kein Bild geliefert.")

    def generate(self, prompt: str, out: Path) -> Path:
        response = self.client.models.generate_content(model=self.model, contents=[prompt])
        return self._save_first_image(response, out)

    def edit(self, image: Path, prompt: str, out: Path) -> Path:
        from PIL import Image

        response = self.client.models.generate_content(
            model=self.model, contents=[prompt, Image.open(image)]
        )
        return self._save_first_image(response, out)


def get_generator(name: str) -> Generator:
    if name == "dummy":
        return DummyGenerator()
    if name == "gemini":
        return GeminiGenerator()
    raise ValueError(f"Unbekannter Generator: {name}")
