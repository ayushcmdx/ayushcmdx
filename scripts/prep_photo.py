#!/usr/bin/env python3
"""
Utility script to prepare and preprocess photograph assets for ASCII art generation.
Performs contrast adjustment, histogram equalization, and format normalization.

Note: This script is only run when updating the source portrait photograph,
keeping heavy image-processing libraries out of the daily GitHub Actions workflow.
"""
import os
import sys
from PIL import Image, ImageOps, ImageEnhance

HERE = os.path.dirname(__file__)
SRC_IMG = os.path.join(HERE, "..", "img", "Ayush_Raj_Face.png")


def preprocess_portrait(input_path, output_path=None, size=(1024, 1024)):
    if output_path is None:
        output_path = input_path

    if not os.path.exists(input_path):
        print(f"Error: source image not found at {input_path}", file=sys.stderr)
        return False

    with Image.open(input_path) as img:
        img = img.convert("RGBA")

        # Square crop from center
        w, h = img.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))

        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)

        img.save(output_path, "PNG", optimize=True)
        print(f"Successfully processed portrait: {output_path} ({size[0]}x{size[1]})")
        return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else SRC_IMG
    preprocess_portrait(target)
