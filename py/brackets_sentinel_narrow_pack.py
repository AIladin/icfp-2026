"""Hand-place the narrow seeded-sentinel pipeline in a 16x17 grid."""

import argparse
from pathlib import Path

from brackets_counter_gen import build as build_counter
from brackets_decoder_seed_gen import build as build_decoder
from brackets_sentinel_zero_pack import Canvas
from brackets_stack3_sentinel_narrow_gen import build as build_stack

ROOT = Path(__file__).resolve().parent.parent


def build() -> str:
    canvas = Canvas()
    canvas.room(1, 1, ["O"])
    canvas.room(1, 6, build_counter())
    canvas.room(4, 1, ["I"])
    canvas.room(7, 1, build_decoder())
    canvas.room(7, 7, build_stack())

    canvas.put(1, 3, "<")
    canvas.put(1, 4, "<")
    canvas.put(4, 3, ">")
    canvas.put(4, 4, "v")
    canvas.put(5, 4, "v")
    canvas.put(15, 4, "v")
    canvas.put(16, 4, ">")
    canvas.put(16, 5, ">")
    canvas.put(5, 13, "^")
    canvas.put(4, 13, "|")
    canvas.put(3, 13, "<")

    text = canvas.render()
    assert len(text.splitlines()) == 17
    assert max(map(len, text.splitlines())) == 16
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "programs" / "brackets" / "v31-sentinel-narrow-16x17.man",
    )
    args = parser.parse_args()
    assert args.out.name != "brackets.man", "refusing to overwrite the live fallback"
    args.out.write_text(build())
    print(f"wrote {args.out} (16x17)")


if __name__ == "__main__":
    main()
