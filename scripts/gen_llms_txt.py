"""Regenerate the llms.txt in the repository root from the same source the running server uses.

    python scripts/gen_llms_txt.py          # rewrite llms.txt
    python scripts/gen_llms_txt.py --check  # exit 1 if it is out of date (CI runs this)

A running server serves the same text with its own address filled in at /llms.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

from bsmm.agent_docs import llms_txt

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "llms.txt"
# The file in the repo cannot know where the user's server lives, so it uses a placeholder an agent must replace.
BASE = "http://YOUR-SERVER:8420"


def main() -> int:
    wanted = llms_txt(BASE)
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != wanted:
            print("llms.txt is out of date: run `python scripts/gen_llms_txt.py`", file=sys.stderr)
            return 1
        return 0
    TARGET.write_text(wanted, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
