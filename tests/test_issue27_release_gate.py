"""A release tag must not publish unless the full CI suite and the Windows smoke pass.

PyYAML is not a declared dev dependency, so these tests read the two workflow files with a
small explicit reader. It understands only the shapes these files use: top-level ``on:`` keys,
two-space job keys, and ``needs`` / ``uses`` / ``cancel-in-progress`` written inline or as a
block list.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

JOB_INDENT = 2
FIELD_INDENT = 4
# Jobs that only build or verify; every other release job publishes something.
GATE_JOBS = {"package", "windows"}


def _lines(name: str) -> list[str]:
    out = []
    for raw in (WORKFLOWS / name).read_text().splitlines():
        line = re.sub(r"\s+#.*$", "", raw).rstrip()
        if line.strip() and not line.lstrip().startswith("#"):
            out.append(line)
    return out


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _top_level_block(lines: list[str], key: str) -> list[str]:
    """Lines nested under a column-zero ``key:``."""
    block: list[str] = []
    inside = False
    for line in lines:
        if _indent(line) == 0:
            inside = line.split(":", 1)[0].strip().strip("'\"") == key
            continue
        if inside:
            block.append(line)
    return block


def _scalar(value: str) -> str:
    return value.strip().strip("'\"")


def _jobs(name: str) -> dict[str, dict[str, list[str]]]:
    """Map job id -> {"needs": [...], "uses": [...]} from a workflow's ``jobs:`` section."""
    jobs: dict[str, dict[str, list[str]]] = {}
    current: dict[str, list[str]] | None = None
    open_list: str | None = None
    for line in _top_level_block(_lines(name), "jobs"):
        indent = _indent(line)
        text = line.strip()
        if indent == JOB_INDENT and text.endswith(":"):
            current = {"needs": [], "uses": []}
            jobs[text[:-1]] = current
            open_list = None
            continue
        if current is None:
            continue
        if indent == FIELD_INDENT:
            open_list = None
            key, _, value = text.partition(":")
            if key == "uses":
                current["uses"].append(_scalar(value))
            elif key == "needs":
                value = value.strip()
                if not value:
                    open_list = "needs"
                elif value.startswith("["):
                    current["needs"] += [_scalar(v) for v in value.strip("[]").split(",") if v.strip()]
                else:
                    current["needs"].append(_scalar(value))
        elif open_list and text.startswith("- "):
            current[open_list].append(_scalar(text[2:]))
    return jobs


def _needs_closure(jobs: dict[str, dict[str, list[str]]], job: str) -> set[str]:
    seen: set[str] = set()
    todo = list(jobs[job]["needs"])
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo += jobs[name]["needs"]
    return seen


def _publishing_jobs(jobs: dict[str, dict[str, list[str]]]) -> list[str]:
    return [
        name
        for name, job in jobs.items()
        if name not in GATE_JOBS and not any(use.endswith("/ci.yml") for use in job["uses"])
    ]


def test_reader_understands_the_release_workflow_shape():
    jobs = _jobs("release.yml")
    assert {"package", "windows", "github-release", "pypi", "docker"} <= set(jobs)
    assert jobs["windows"]["uses"] == ["./.github/workflows/windows.yml"]
    assert jobs["package"]["needs"] == []


def test_ci_can_be_called_by_the_release_workflow():
    triggers = [line.strip().rstrip(":") for line in _top_level_block(_lines("ci.yml"), "on") if _indent(line) == 2]
    assert "workflow_call" in triggers
    # The push and pull_request triggers still run ordinary CI.
    assert {"push", "pull_request"} <= set(triggers)


def test_called_ci_never_cancels_a_release_or_main_run():
    cancel = [
        line.strip()
        for line in _top_level_block(_lines("ci.yml"), "concurrency")
        if line.strip().startswith("cancel-in-progress:")
    ]
    assert len(cancel) == 1
    # A literal true would let one run cancel another that shares its ref.
    assert cancel[0].split(":", 1)[1].strip() != "true"


def test_every_publishing_job_needs_ci_and_windows():
    jobs = _jobs("release.yml")
    ci_jobs = [name for name, job in jobs.items() if any(use.endswith("/ci.yml") for use in job["uses"])]
    assert ci_jobs, "release.yml must call .github/workflows/ci.yml"
    publishing = _publishing_jobs(jobs)
    assert {"github-release", "pypi", "docker"} <= set(publishing)
    for name in publishing:
        needed = _needs_closure(jobs, name)
        assert "package" in needed, f"{name} does not wait for the package build"
        assert "windows" in needed, f"{name} does not wait for the Windows smoke"
        assert set(ci_jobs) & needed, f"{name} does not wait for the full CI suite"


USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)")
PINNED_REF = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
LOCAL_WORKFLOW_PREFIX = "./.github/workflows/"
LOCAL_PREFIX = "./"


def _uses_refs(name: str) -> list[str]:
    """Every ``uses:`` value (job-level and step-level) in one workflow file."""
    refs = []
    for line in _lines(name):
        match = USES_LINE.match(line)
        if match:
            refs.append(_scalar(match["ref"]))
    return refs


def _workflows_reachable_from(entry: str) -> list[str]:
    """``entry`` plus every local reusable workflow it calls, transitively."""
    seen: list[str] = []
    todo = [entry]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.append(name)
        todo += [
            ref[len(LOCAL_WORKFLOW_PREFIX):]
            for ref in _uses_refs(name)
            if ref.startswith(LOCAL_WORKFLOW_PREFIX)
        ]
    return seen


def test_release_run_reaches_the_called_workflows():
    assert set(_workflows_reachable_from("release.yml")) >= {"release.yml", "ci.yml", "windows.yml"}


def test_every_action_reachable_from_the_release_run_is_pinned_to_a_commit_sha():
    unpinned = []
    for workflow in _workflows_reachable_from("release.yml"):
        for ref in _uses_refs(workflow):
            if not ref.startswith(LOCAL_PREFIX) and not PINNED_REF.match(ref):
                unpinned.append(f"{workflow}: {ref}")
    assert not unpinned, "actions in the release run not pinned to a 40-hex commit SHA:\n" + "\n".join(unpinned)
