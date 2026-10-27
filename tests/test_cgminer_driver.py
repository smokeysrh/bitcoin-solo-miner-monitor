import pytest

from bsmm.drivers.base import BadResponse, Unreachable
from bsmm.drivers.cgminer import (
    CgminerDriver,
    cgminer_call,
    classify,
    parse_avalon_estats,
    parse_bracket_fields,
    parse_cgminer_text,
    parse_pools,
    parse_summary,
)
from bsmm.net import make_http_client
from bsmm.sim.cgminer import CgminerSim

# The MM ID0 string format documented in the old v0.9.3 notes (Avalon Nano 3).
OLD_REPO_SAMPLE = "Temp[38] OTemp[38] TMax[87] TAvg[85] Fan1[2430] FanR[32%] MGHS[3090.53] Freq[500.00] HVer[MM3v1_X3] DNA[0123456789abcdef]"


def test_bracket_parser_handles_values_with_spaces_and_percent():
    f = parse_bracket_fields("Ver[Nano3-1] MW[340560 340538] FanR[32%] DH[2.749%]")
    assert f == {"Ver": "Nano3-1", "MW": "340560 340538", "FanR": "32%", "DH": "2.749%"}


def test_avalon_estats_from_documented_sample():
    out = parse_avalon_estats([{"MM ID0": OLD_REPO_SAMPLE}])
    assert out["temp_asic_c"] == 85  # chip average, not the inlet sensor
    assert out["temp_board_c"] == 38
    assert out["fan_rpm"] == 2430 and out["fan_pct"] == 32
    assert out["hashrate_hs"] == pytest.approx(3090.53e9)
    assert out["frequency_mhz"] == pytest.approx(500.0)
    assert out["dna"] == "0123456789abcdef"


def test_avalon_estats_sums_modules():
    out = parse_avalon_estats(
        [{"MM ID0": "TAvg[80] TMax[90] GHSmm[1000.0] Fan1[3000] FanR[40%]", "MM ID1": "TAvg[84] TMax[91] GHSmm[2000.0] Fan1[3100] FanR[45%]"}]
    )
    assert out["hashrate_hs"] == pytest.approx(3000e9)
    assert out["temp_asic_c"] == 84 and out["fan_pct"] == 45 and out["fan_rpm"] == 3100


def test_parse_cgminer_text_variants():
    assert parse_cgminer_text(b'{"STATUS":[{"STATUS":"S"}]}\x00')["STATUS"][0]["STATUS"] == "S"
    assert parse_cgminer_text('{"a":1}{"b":2}') == {"a": 1}  # '}{' concatenation keeps the first object
    with pytest.raises(BadResponse):
        parse_cgminer_text(b"\x00")
    with pytest.raises(BadResponse):
        parse_cgminer_text("not json")
    with pytest.raises(BadResponse):
        parse_cgminer_text("[1,2]")


@pytest.mark.parametrize(
    ("version", "family", "model"),
    [
        ({"PROD": "Avalonnano", "MODEL": "nano3"}, "avalon", "Avalon Nano 3"),
        ({"PROD": "Avalonnano", "MODEL": "nano3s"}, "avalon", "Avalon Nano 3S"),
        ({"PROD": "AvalonQ", "MODEL": "Q"}, "avalon", "Avalon Q"),
        ({"BMMiner": "2.0.0", "Type": "Antminer S19j Pro"}, "antminer", "Antminer S19j Pro"),
        ({"BOSminer": "bosminer-plus-am1-s9", "Type": "Antminer S9"}, "braiins", "Antminer S9"),
        ({"LUXminer": "2024.1"}, "luxos", "LuxOS miner"),
        ({"CGMiner": "4.11.1"}, "cgminer", "cgminer device"),
    ],
)
def test_classify(version, family, model):
    assert classify(version) == (family, model)


def test_summary_units():
    s = parse_summary({"MHS 5s": 3900000.0, "MHS av": 3800000.0, "Accepted": 10, "Rejected": 1, "Best Share": "2.3G", "Elapsed": 99, "Found Blocks": 0})
    assert s["hashrate_now"] == pytest.approx(3.9e12)
    assert s["hashrate_avg"] == pytest.approx(3.8e12)
    assert s["best_share"] == pytest.approx(2.3e9)
    s2 = parse_summary({"GHS 5s": "104000.5"})
    assert s2["hashrate_now"] == pytest.approx(104000.5e9)


def test_pools_parse_active_and_priority():
    pools = parse_pools(
        [
            {"URL": "stratum+tcp://solo.ckpool.org:3333", "User": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq.b", "Status": "Alive", "Priority": 1},
            {"URL": "stratum+tcp://192.168.1.10:2018", "User": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq.a", "Status": "Alive", "Priority": 0, "Stratum Active": True},
        ]
    )
    assert [p.role for p in pools] == ["primary", "fallback"]
    assert pools[0].url == "192.168.1.10" and pools[0].port == 2018 and pools[0].active
    assert pools[0].worker == "a" and pools[0].address


@pytest.fixture
async def avalon():
    sim = await CgminerSim("avalon_nano3", seed=1).start()
    yield sim
    await sim.stop()


@pytest.fixture
async def antminer():
    sim = await CgminerSim("antminer_s19", seed=2).start()
    yield sim
    await sim.stop()


async def test_probe_and_poll_avalon(avalon):
    async with make_http_client() as client:
        res = await CgminerDriver.probe("127.0.0.1", avalon.port, client=client)
        assert res is not None
        assert res.info.family == "avalon" and res.info.model == "Avalon Nano 3"
        assert res.info.serial == "0123456789abcdef"
        assert res.info.identity_key == "serial:0123456789abcdef"
        assert res.info.extra["monitor_only"] is True
        d = CgminerDriver("127.0.0.1", avalon.port, client=client, info=res.info)
        t = await d.poll()
    assert t.hashrate_hs == pytest.approx(3900e9)  # module total from estats
    assert t.temp_asic_c == 85 and t.temp_board_c == 38
    assert t.fan_pct == 32 and t.fan_rpm == 2430
    assert t.frequency_mhz == 500
    assert t.best_diff == 2_345_678_901
    assert t.pools[0].active and t.pools[0].port == 2018
    assert t.using_fallback is False
    assert t.power_w is None and t.efficiency_j_th is None  # the device does not report power: we don't invent it


async def test_manual_power_makes_efficiency_available(avalon):
    async with make_http_client() as client:
        res = await CgminerDriver.probe("127.0.0.1", avalon.port, client=client)
        assert res is not None
        res.info.extra["power_override_w"] = 140.0
        d = CgminerDriver("127.0.0.1", avalon.port, client=client, info=res.info)
        t = await d.poll()
    assert t.power_w == 140.0 and t.power_source == "manual"
    assert t.efficiency_j_th == pytest.approx(140.0 / 3.9)


async def test_probe_and_poll_antminer(antminer):
    async with make_http_client() as client:
        res = await CgminerDriver.probe("127.0.0.1", antminer.port, client=client)
        assert res is not None and res.info.family == "antminer" and res.info.model == "Antminer S19j Pro"
        d = CgminerDriver("127.0.0.1", antminer.port, client=client, info=res.info)
        t = await d.poll()
    assert t.hashrate_hs == pytest.approx(104_000e9, rel=0.02)
    assert t.temp_asic_c == 79  # the hottest chip sensor
    assert t.fan_rpm == 5760
    assert t.frequency_mhz == 525
    assert t.hashrate_expected_hs == pytest.approx(104_000e9)


async def test_probe_non_cgminer_port_returns_none():
    async with make_http_client() as client:
        assert await CgminerDriver.probe("127.0.0.1", 9, client=client, timeout=1) is None  # discard port: closed


async def test_unreachable_poll_raises():
    async with make_http_client() as client:
        d = CgminerDriver("127.0.0.1", 9, client=client, timeout=1)
        with pytest.raises(Unreachable):
            await d.poll()


async def test_cgminer_call_unknown_command(avalon):
    reply = await cgminer_call("127.0.0.1", avalon.port, "bogus", timeout=2)
    assert reply["STATUS"][0]["STATUS"] == "E"
