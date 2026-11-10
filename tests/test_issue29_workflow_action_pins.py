"""Publishing workflows must run third-party actions from reviewed, immutable commits (issue #29).

A moving tag such as ``@v4`` changes the code a credential-bearing job executes without any change
to this repository. Every non-local ``uses:`` reference must be a full 40-hex commit SHA with a
trailing ``# <version>`` comment so a reviewer can read what was pinned.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLISHING_WORKFLOWS = (".github/workflows/release.yml", ".github/workflows/windows.yml")

USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
PINNED_REF = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s+#\s*\S+")
LOCAL_PREFIX = "./"


def external_uses(workflow: str) -> list[tuple[int, str, str]]:
    """Return (line number, reference, text after the reference) for every non-local ``uses:``."""
    found = []
    for number, line in enumerate((ROOT / workflow).read_text().splitlines(), start=1):
        match = USES_LINE.match(line)
        if match and not match["ref"].startswith(LOCAL_PREFIX):
            found.append((number, match["ref"], match["rest"]))
    return found


@pytest.mark.parametrize("workflow", PUBLISHING_WORKFLOWS)
def test_external_actions_are_pinned_to_full_commit_shas(workflow):
    references = external_uses(workflow)
    assert references, f"{workflow} has no external actions; the check would pass vacuously"
    unpinned = [f"{workflow}:{number} {ref}" for number, ref, _ in references if not PINNED_REF.match(ref)]
    assert not unpinned, "actions not pinned to a 40-hex commit SHA:\n" + "\n".join(unpinned)


@pytest.mark.parametrize("workflow", PUBLISHING_WORKFLOWS)
def test_pinned_actions_keep_a_readable_version_comment(workflow):
    missing = [
        f"{workflow}:{number} {ref}"
        for number, ref, rest in external_uses(workflow)
        if not VERSION_COMMENT.match(rest)
    ]
    assert not missing, "pinned actions need a trailing '# <version>' comment:\n" + "\n".join(missing)
