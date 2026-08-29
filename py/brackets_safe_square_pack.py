"""Hand-place the fully safe brackets pipeline in a 16x16 square."""

import argparse
from pathlib import Path

from brackets_counter_flat_gen import build as build_counter
from brackets_decoder_seed_gen import build as build_decoder
from brackets_sentinel_zero_pack import Canvas
from brackets_stack3_sentinel_narrow_gen import build as build_stack

ROOT = Path(__file__).resolve().parent.parent


def build() -> str:
    canvas = Canvas()
    canvas.room(1, 1, ["O"])
    canvas.room(1, 5, build_counter())
    canvas.room(5, 1, ["I"])
    canvas.room(8, 1, build_decoder())
    canvas.room(6, 7, build_stack())

    # counter -> output through the one-row gap between the I/O rooms
    canvas.put(3, 3, "<")
    canvas.put(3, 2, "^")

    # input -> decoder down the counter's west clearance
    canvas.put(5, 3, ">")
    canvas.put(5, 4, "v")
    canvas.put(6, 4, "v")

    # decoder -> stack around their adjacent top corners
    canvas.put(6, 5, "^")
    canvas.put(5, 5, ">")

    # stack -> counter around their adjacent east corners
    canvas.put(4, 15, "^")
    canvas.put(3, 15, "<")

    text = canvas.render()
    assert len(text.splitlines()) == 16
    assert max(map(len, text.splitlines())) == 16
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "programs" / "brackets" / "v33-safe-16x16.man",
    )
    args = parser.parse_args()
    assert args.out.name != "brackets.man", "refusing to overwrite the live fallback"
    args.out.write_text(build())
    print(f"wrote {args.out} (16x16)")


if __name__ == "__main__":
    main()
