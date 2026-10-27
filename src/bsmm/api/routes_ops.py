"""Prometheus metrics, the agent guide / llms.txt and demo-mode helpers."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from bsmm import __version__
from bsmm.agent_docs import agent_guide, llms_txt
from bsmm.api.deps import get_ctx, require
from bsmm.api.errors import ApiError, bad_request, not_found
from bsmm.auth import Principal
from bsmm.context import AppContext
from bsmm.drivers.sim import _AXEOS
from bsmm.engine.odds import build_odds
from bsmm.models import DeviceStatus, DeviceView, Telemetry

router = APIRouter()
ops_router = APIRouter()  # mounted at the root (/metrics, /llms.txt)


# ------------------------------------------------------------------------------------------ metrics


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _labels(**kw: str) -> str:
    return "{" + ",".join(f'{k}="{_esc(str(v))}"' for k, v in kw.items()) + "}" if kw else ""


async def render_metrics(ctx: AppContext) -> str:
    out: list[str] = []

    def metric(name: str, help_: str, kind: str = "gauge") -> None:
        out.append(f"# HELP {name} {help_}")
        out.append(f"# TYPE {name} {kind}")

    def sample(metric_name: str, value: float | int | None, **labels: str) -> None:
        if value is not None:
            out.append(f"{metric_name}{_labels(**labels)} {float(value):.10g}")

    views = ctx.fleet.views()
    summary = ctx.fleet.summary(fresh=True)
    metric("bsmm_info", "Build information")
    sample("bsmm_info", 1, version=__version__)
    metric("bsmm_devices", "Number of monitored miners by status")
    for st in DeviceStatus:
        sample("bsmm_devices", sum(1 for v in views if v.status == st), status=st.value)
    metric("bsmm_fleet_hashrate_hashes_per_second", "Total smoothed hashrate of all miners")
    sample("bsmm_fleet_hashrate_hashes_per_second", summary.hashrate_hs)
    metric("bsmm_fleet_power_watts", "Total power draw reported by the miners")
    sample("bsmm_fleet_power_watts", summary.power_w)
    metric("bsmm_fleet_efficiency_joules_per_terahash", "Fleet efficiency (lower is better)")
    sample("bsmm_fleet_efficiency_joules_per_terahash", summary.efficiency_j_th)

    per: list[tuple[str, str, Callable[[DeviceView, Telemetry | None], float | None], str]] = [
        ("bsmm_device_up", "1 if the miner answered its last poll", lambda v, t: 0 if v.status == DeviceStatus.OFFLINE else 1, "gauge"),
        ("bsmm_device_hashrate_hashes_per_second", "Smoothed hashrate", lambda v, t: v.hashrate_smooth_hs, "gauge"),
        ("bsmm_device_power_watts", "Power draw", lambda v, t: t.power_w if t else None, "gauge"),
        ("bsmm_device_efficiency_joules_per_terahash", "Efficiency", lambda v, t: t.efficiency_j_th if t else None, "gauge"),
        ("bsmm_device_temperature_asic_celsius", "ASIC temperature", lambda v, t: t.temp_asic_c if t else None, "gauge"),
        ("bsmm_device_temperature_vr_celsius", "Voltage regulator temperature", lambda v, t: t.temp_vr_c if t else None, "gauge"),
        ("bsmm_device_fan_rpm", "Fan speed", lambda v, t: t.fan_rpm if t else None, "gauge"),
        ("bsmm_device_frequency_mhz", "ASIC frequency", lambda v, t: t.frequency_mhz if t else None, "gauge"),
        ("bsmm_device_shares_accepted_total", "Accepted shares since the miner booted", lambda v, t: t.shares_accepted if t else None, "counter"),
        ("bsmm_device_shares_rejected_total", "Rejected shares since the miner booted", lambda v, t: t.shares_rejected if t else None, "counter"),
        ("bsmm_device_best_share_difficulty", "Best share difficulty", lambda v, t: t.best_diff if t else None, "gauge"),
        ("bsmm_device_uptime_seconds", "Miner uptime", lambda v, t: t.uptime_s if t else None, "gauge"),
        ("bsmm_device_wifi_rssi_dbm", "WiFi signal", lambda v, t: t.wifi_rssi_dbm if t else None, "gauge"),
    ]
    for name, help_, fn, kind in per:
        metric(name, help_, kind)
        for v in views:
            sample(name, fn(v, v.telemetry), device=v.id, name=v.name, model=v.display_model)

    n = ctx.network.state
    metric("bsmm_network_block_height", "Current block height")
    sample("bsmm_network_block_height", n.height)
    metric("bsmm_network_difficulty", "Current network difficulty")
    sample("bsmm_network_difficulty", n.difficulty)
    metric("bsmm_network_hashrate_hashes_per_second", "Estimated network hashrate")
    sample("bsmm_network_hashrate_hashes_per_second", n.network_hashrate_hs)
    odds = build_odds(summary, n, ctx.settings.current)
    if odds.get("available"):
        metric("bsmm_block_probability_per_year", "Probability of finding at least one block in a year at the current hashrate")
        sample("bsmm_block_probability_per_year", odds["horizons"]["year"]["probability"])
    metric("bsmm_blocks_found_total", "Blocks found by you")
    sample("bsmm_blocks_found_total", len(await ctx.store.list_blocks_found()), )
    metric("bsmm_source_up", "1 if a configured node/pool/data source answered its last poll")
    for h in n.sources:
        sample("bsmm_source_up", 1 if h.ok else 0, source=h.name, kind=h.kind)
    metric("bsmm_alerts_active", "Number of alerts currently firing")
    sample("bsmm_alerts_active", len(ctx.alerts.active_alerts()))
    return "\n".join(out) + "\n"


@ops_router.get("/metrics", include_in_schema=True, tags=["system"], operation_id="getMetrics", summary="Prometheus metrics",
                response_class=PlainTextResponse)
async def metrics(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> PlainTextResponse:
    return PlainTextResponse(await render_metrics(ctx), media_type="text/plain; version=0.0.4; charset=utf-8")


# ------------------------------------------------------------------------------------------ agents


@router.get("/agent/guide", tags=["agents"], operation_id="getAgentGuide",
            summary="How an AI agent can set up and operate this app for a user (machine-readable)")
async def guide(request: Request, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    return agent_guide(str(request.base_url).rstrip("/"), auth_mode=ctx.settings.current.auth.mode, demo=ctx.config.demo)


@ops_router.get("/llms.txt", include_in_schema=False, response_class=PlainTextResponse)
async def llms(request: Request) -> PlainTextResponse:
    return PlainTextResponse(llms_txt(str(request.base_url).rstrip("/")), media_type="text/markdown; charset=utf-8")


# ------------------------------------------------------------------------------------------ demo


class ScenarioBody(BaseModel):
    scenario: str  # block | offline | online | hot | cool
    device: str | None = None


@router.post("/demo/scenario", tags=["demo"], operation_id="runDemoScenario", summary="Demo mode only: trigger a situation to see how the app reacts",
             description="`block` (celebration), `offline` / `online` (a miner drops and returns), `hot` / `cool` (overheating).")
async def demo_scenario(body: ScenarioBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    if not ctx.config.demo:
        raise ApiError(409, "not_demo", "This only works in demo mode (`bsmm serve --demo`).")
    if body.scenario == "block":
        from bsmm.sources.base import BlockInfo

        h = (ctx.network.state.height or 972_175) + 1
        block = BlockInfo(hash=f"{h:064x}", height=h, ts=__import__("time").time(), tx_count=3500, pool_name="You", reward_sats=321_500_000,
                          coinbase_addresses=ctx.fleet.all_addresses()[:1])
        await ctx.network.record_block_found(block, block.coinbase_addresses[0] if block.coinbase_addresses else None, source="demo")
        return {"ok": True, "scenario": "block"}
    views = ctx.fleet.views()
    target = next((v for v in views if body.device in (v.id, v.name)), None) if body.device else (views[2] if len(views) > 2 else (views[0] if views else None))
    if target is None:
        raise not_found("A demo miner")
    sim = _AXEOS.get(target.host)
    if sim is None:
        raise bad_request("That demo miner does not support this scenario.")
    if body.scenario == "offline":
        sim.fail_next = 10**9
    elif body.scenario == "online":
        sim.fail_next = 0
    elif body.scenario == "hot":
        sim.profile = dataclasses.replace(sim.profile, temp_per_w=sim.profile.temp_per_w * 3.2)
    elif body.scenario == "cool":
        sim.profile = dataclasses.replace(sim.profile, temp_per_w=sim.profile.temp_per_w / 3.2)
    else:
        raise bad_request("Unknown scenario.", "Use block, offline, online, hot or cool.")
    return {"ok": True, "scenario": body.scenario, "device": target.name}
