from __future__ import annotations

import argparse
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor


def main() -> None:
    args = _parse_args()
    model_dir = args.model_dir.resolve()
    image_path = args.image.resolve()

    image = Image.open(image_path).convert("RGB")
    if args.crop:
        image = image.crop(tuple(args.crop))
        if args.output_crop:
            args.output_crop.parent.mkdir(parents=True, exist_ok=True)
            image.save(args.output_crop)

    processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        str(model_dir),
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": args.prompt},
            ],
        }
    ]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt")

    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
        )

    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(text)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/SmolVLM-500M-Instruct"),
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument(
        "--prompt",
        default="Lee este recorte de un formulario. Responde solo con el texto que puedas ver, sin explicar.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=80)
    parser.add_argument(
        "--crop",
        type=int,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        help="Recorte opcional en pixeles sobre la imagen de entrada.",
    )
    parser.add_argument("--output-crop", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    main()
