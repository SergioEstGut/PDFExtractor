from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor


def main() -> None:
    args = _parse_args()
    model_dir = args.model_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    processor = AutoProcessor.from_pretrained(
        str(model_dir),
        local_files_only=True,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        str(model_dir),
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()

    candidatos = _cargar_candidatos(args.candidates, limit=args.limit)
    image = Image.open(args.image).convert("RGB")
    tesseract = _cargar_tesseract(args.tesseract)

    resultados = []
    for index, candidato in enumerate(candidatos, start=1):
        crop = _recorte_candidato(image, tesseract, candidato, args.margin)
        crop_path = output_dir / f"{index:02d}_{candidato['seccion']}_{candidato['campo']}.png"
        crop.save(crop_path)

        prompt = _prompt(candidato)
        started = time.perf_counter()
        respuesta = _preguntar(model, processor, crop, prompt, args.max_new_tokens)
        elapsed = round(time.perf_counter() - started, 2)

        resultados.append(
            {
                "seccion": candidato["seccion"],
                "campo": candidato["campo"],
                "tipo_candidato": candidato.get("tipo_candidato", ""),
                "valor_pdf": candidato.get("valor_pdf", ""),
                "valor_ocr": candidato.get("valor_ocr", ""),
                "crop": str(crop_path),
                "prompt": prompt,
                "respuesta": respuesta,
                "segundos": elapsed,
            }
        )
        print(f"{index}/{len(candidatos)} {candidato['seccion']}.{candidato['campo']} -> {respuesta!r} ({elapsed}s)")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cargar_candidatos(path: Path, limit: int) -> list[dict[str, Any]]:
    candidatos = json.loads(path.read_text(encoding="utf-8-sig"))
    candidatos = [
        candidato
        for candidato in candidatos
        if candidato.get("tipo_candidato") in {"solo_pdf", "solo_ocr", "diferente"}
    ]
    return candidatos[:limit] if limit else candidatos


def _cargar_tesseract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))["ocr"]


def _recorte_candidato(
    image: Image.Image,
    tesseract: dict[str, Any],
    candidato: dict[str, Any],
    margin: int,
) -> Image.Image:
    aliases = _aliases_desde_prompt(candidato.get("prompt", ""))
    aliases.extend(_aliases_desde_nombre(candidato["campo"]))
    line = _buscar_linea(tesseract.get("lines", []), aliases)
    if line is None:
        return image.crop((0, 0, image.width, image.height))

    label_bbox = _buscar_bbox_alias_en_linea(line, aliases)
    if label_bbox is None:
        x0 = max(0, int(line["x0"]) - margin)
        x1 = min(image.width, int(line["x1"]) + margin)
    else:
        x0 = max(0, label_bbox[0] - 95)
        x1 = min(image.width, label_bbox[2] + 55)

    y0 = max(0, int(line["y0"]) - margin)
    y1 = min(image.height, int(line["y1"]) + margin)

    if x1 - x0 < 220:
        x0 = max(0, x0 - 40)
        x1 = min(image.width, x1 + 80)
    if y1 - y0 < 90:
        y0 = max(0, y0 - 35)
        y1 = min(image.height, y1 + 55)
    return image.crop((x0, y0, x1, y1))


def _buscar_bbox_alias_en_linea(
    line: dict[str, Any],
    aliases: list[str],
) -> tuple[int, int, int, int] | None:
    token_positions: list[tuple[str, dict[str, Any]]] = []
    for word in line.get("words", []):
        for token in _tokens(word.get("text", "")):
            token_positions.append((token, word))

    for alias in aliases:
        alias_tokens = _tokens(alias)
        if not alias_tokens:
            continue
        for start in range(0, len(token_positions) - len(alias_tokens) + 1):
            current = [token for token, _ in token_positions[start : start + len(alias_tokens)]]
            if current != alias_tokens:
                continue
            words = [word for _, word in token_positions[start : start + len(alias_tokens)]]
            return (
                min(int(word["x0"]) for word in words),
                min(int(word["y0"]) for word in words),
                max(int(word["x1"]) for word in words),
                max(int(word["y1"]) for word in words),
            )
    return None


def _buscar_linea(lines: list[dict[str, Any]], aliases: list[str]) -> dict[str, Any] | None:
    mejores: list[tuple[int, dict[str, Any]]] = []
    aliases_norm = [_normalizar(alias) for alias in aliases if alias]
    for line in lines:
        texto = _normalizar(line.get("text", ""))
        score = 0
        for alias in aliases_norm:
            partes = [p for p in alias.split() if len(p) > 1]
            if alias and alias in texto:
                score += 100
            score += sum(1 for parte in partes if parte in texto)
        if score:
            mejores.append((score, line))
    if not mejores:
        return None
    mejores.sort(key=lambda item: item[0], reverse=True)
    return mejores[0][1]


def _aliases_desde_prompt(prompt: str) -> list[str]:
    match = re.search(r'"aliases":\s*(\[[^\]]*\])', prompt)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def _aliases_desde_nombre(nombre: str) -> list[str]:
    limpio = nombre.replace("_txt", "").replace("_", " ")
    return [limpio, limpio.replace("  ", " ")]


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for old, new in replacements.items():
        texto = texto.replace(old, new)
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _tokens(texto: str) -> list[str]:
    return [token for token in _normalizar(texto).split() if token]


def _prompt(candidato: dict[str, Any]) -> str:
    return (
        "Lee el recorte del formulario y resuelve solo el campo indicado. "
        "No inventes datos. Responde con una sola palabra: Si, No, SIN_RESOLVER "
        "o el valor literal si se lee claramente. "
        f"Campo: {candidato['seccion']}.{candidato['campo']}. "
        f"Tipo esperado: {candidato.get('tipo', '')}. "
        f"Lectura PDF: {candidato.get('valor_pdf', '')!r}. "
        f"Lectura OCR: {candidato.get('valor_ocr', '')!r}. "
        "Para checks usa exactamente Si o No. Si no se ve claro usa SIN_RESOLVER."
    )


def _preguntar(
    model: Any,
    processor: Any,
    image: Image.Image,
    prompt: str,
    max_new_tokens: int,
) -> str:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=text, images=[image], return_tensors="pt")
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
        )
    generated = generated[:, inputs["input_ids"].shape[1] :]
    return processor.batch_decode(generated, skip_special_tokens=True)[0].strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=Path("models/Qwen2.5-VL-3B-Instruct"))
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--tesseract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--margin", type=int, default=45)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--min-pixels", type=int, default=3136)
    parser.add_argument("--max-pixels", type=int, default=16384)
    return parser.parse_args()


if __name__ == "__main__":
    main()
