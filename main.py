"""Entry point for the food-picture-01 submission.

The picture ships next to this file as ``entry.png``.  Running the
script checks the picture against the contest limits and then copies
it, untouched, into the directory the grader points us at.
"""

import hashlib
import os
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576
MAX_SIDE = 1024

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8"


def fail(reason):
    """Abort with a readable complaint on stderr."""
    print(f"entry check failed: {reason}", file=sys.stderr)
    raise SystemExit(1)


def png_dimensions(blob):
    """Pull width and height out of the PNG IHDR chunk."""
    if len(blob) < 24 or blob[12:16] != b"IHDR":
        fail("PNG header is truncated or missing its IHDR chunk")
    width, height = struct.unpack(">II", blob[16:24])
    return width, height


def jpeg_dimensions(blob):
    """Walk JPEG segments until a start-of-frame marker turns up."""
    pos = 2  # the SOI marker itself carries no payload
    while pos + 4 <= len(blob):
        if blob[pos] != 0xFF:
            fail("JPEG segment does not start where one was expected")
        marker = blob[pos + 1]
        if marker in (0xC0, 0xC2):  # SOF0 / SOF2 hold the frame size
            height, width = struct.unpack(">HH", blob[pos + 5:pos + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            pos += 2  # standalone markers have no length field
            continue
        (span,) = struct.unpack(">H", blob[pos + 2:pos + 4])
        if span < 2:
            fail("JPEG segment declares an impossible length")
        pos += 2 + span
    fail("no start-of-frame segment found in JPEG data")


def measure(blob):
    """Recognise the picture format and return (format, width, height)."""
    if blob.startswith(PNG_MAGIC):
        width, height = png_dimensions(blob)
        return "PNG", width, height
    if blob.startswith(JPEG_MAGIC):
        width, height = jpeg_dimensions(blob)
        return "JPEG", width, height
    fail(
        "picture is neither PNG nor JPEG "
        f"(first bytes {blob[:4].hex() or 'none'}, expected PNG or JPEG magic)"
    )


def main():
    here = Path(__file__).resolve().parent
    blob = (here / "entry.png").read_bytes()

    if len(blob) > MAX_BYTES:
        fail(
            f"picture is {len(blob)} bytes, over the {MAX_BYTES}-byte limit"
        )
    fmt, width, height = measure(blob)
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
        fail(
            f"picture dimensions are {width}x{height}, outside the "
            f"allowed 1..{MAX_SIDE} range per side"
        )

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    target.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    print(
        f"Entry written to {target}: {fmt}, {len(blob)} bytes, "
        f"{width}x{height}, sha256 {digest}"
    )


if __name__ == "__main__":
    main()
