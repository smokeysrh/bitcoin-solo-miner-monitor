"""bsmm capture: read-only replies with private data removed."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from bsmm.capture import REDACTED, redact
from bsmm.cli.main import app

ADDRESS = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


def test_redact_by_key_and_by_pattern():
    raw = {
        "ssid": "MyHomeWifi", "macAddr": "10:20:30:2B:42:E4", "hostname": "bitaxe",
        "stratumUser": f"{ADDRESS}.rig1", "stratumURL": "pool.example.com", "ASICModel": "BM1370",
        "pools": [{"URL": "stratum+tcp://a:3333", "User": ADDRESS}],
        "note": f"paid to {ADDRESS} from 10-20-30-2B-42-E4",
        "temps": [41.5, 42],
    }
    out = redact(raw)
    assert out["ssid"] == REDACTED and out["macAddr"] == REDACTED and out["stratumUser"] == REDACTED
    assert out["stratumURL"] == REDACTED and out["pools"][0]["URL"] == REDACTED and out["pools"][0]["User"] == REDACTED
    # what identifies the model survives
    assert out["ASICModel"] == "BM1370" and out["hostname"] == "bitaxe" and out["temps"] == [41.5, 42]
    # free text is scrubbed by pattern
    assert ADDRESS not in json.dumps(out) and "2B-42-E4" not in json.dumps(out) and "2B:42:E4" not in json.dumps(out)


def test_redact_does_not_change_the_input():
    raw = {"ssid": "x"}
    redact(raw)
    assert raw == {"ssid": "x"}


def test_capture_command_reports_an_unreachable_host_plainly():
    # 192.0.2.0/24 is reserved for documentation; nothing answers there
    res = CliRunner().invoke(app, ["capture", "192.0.2.1", "--timeout", "0.3"])
    assert res.exit_code == 0
    assert "Nothing at 192.0.2.1 answered" in res.output
