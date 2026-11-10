"""Turn a release tag into the canonical package version and its channel, in one place.

    python scripts/release_version.py v1.2.0-rc.1              # version=1.2.0rc1 / is_prerelease=true
    python scripts/release_version.py v1.2.0-rc.1 --canonical  # 1.2.0rc1

The first form prints GitHub Actions output lines. Accepted tags are ``vX.Y.Z`` and a pre-release written either
the PEP 440 way (``aN``, ``bN``, ``rcN``) or with a hyphen (``-alpha.N``, ``-beta.N``, ``-rc.N``, ``-rcN``).
Anything else is refused, so a tag that is not understood can never reach the stable channel.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import NamedTuple

from packaging.version import Version

TAG = re.compile(
    r"v(?P<base>\d+\.\d+\.\d+)"
    r"(?:(?:-(?P<word>alpha|beta|rc)\.?|(?P<short>a|b|rc))(?P<number>\d+))?"
)
HYPHEN_WORDS = {"alpha": "a", "beta": "b", "rc": "rc"}


class ParsedTag(NamedTuple):
    version: str
    is_prerelease: bool


def parse_tag(tag: str) -> ParsedTag:
    match = TAG.fullmatch(tag)
    if match is None:
        raise ValueError(f"Unsupported release tag {tag!r}: use vX.Y.Z, vX.Y.ZaN/bN/rcN or vX.Y.Z-rc.N")
    marker = HYPHEN_WORDS[match["word"]] if match["word"] else (match["short"] or "")
    parsed = Version(f"{match['base']}{marker}{match['number'] or ''}")
    return ParsedTag(str(parsed), parsed.is_prerelease)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("tag")
    parser.add_argument("--canonical", action="store_true", help="print only the canonical version")
    args = parser.parse_args(argv)
    try:
        parsed = parse_tag(args.tag)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.canonical:
        print(parsed.version)
    else:
        print(f"version={parsed.version}")
        print(f"is_prerelease={str(parsed.is_prerelease).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
