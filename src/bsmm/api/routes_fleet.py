"""Miners, fleet totals, history, discovery and the live stream."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from bsmm.api.deps import get_ctx, require
from bsmm.api.errors import ApiError, bad_request, not_found
from bsmm.api.util import csv_list, window
from bsmm.auth import Principal
from bsmm.context import AppContext
from bsmm.engine.odds import build_odds
from bsmm.models import DeviceStatus, DeviceView, FleetSummary
from bsmm.net import split_host_port
from bsmm.storage import metrics as mx

router = APIRouter()


# ------------------------------------------------------------------------------------------ overview


@router.get(
    "/overview",
    tags=["fleet"],
    operation_id="getOverview",
    summary="Everything the dashboard shows, in one call",
    description="Fleet totals, solo-mining odds, network state, active alerts, recent events and blocks you found. "
    "The best single call for an AI agent that wants to understand the user's whole setup.",
)
async def overview(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    summary = ctx.fleet.summary(fresh=True)
    work_hashes, work_blocks = ctx.fleet.work
    found = await ctx.store.list_blocks_found()
    net = ctx.network.state
    odds = build_odds(summary, net, ctx.settings.current, work_hashes=work_hashes, expected_blocks_of_work=work_blocks, blocks_found=len(found))
    events = await ctx.store.list_events(limit=8)
    return {
        "summary": summary.model_dump(mode="json"),
        "odds": odds,
        "network": net.model_dump(mode="json", exclude={"recent_blocks", "pools"}),
        "alerts": ctx.alerts.active_alerts(),
        "events": [e.model_dump(mode="json") for e in events],
        "blocks_found": found,
        "leaderboard": await ctx.store.best_shares_leaderboard(5),
        "demo": ctx.config.demo,
    }


@router.get("/fleet", tags=["fleet"], operation_id="getFleetSummary", summary="Fleet totals: hashrate, power, efficiency, counts")
async def fleet(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> FleetSummary:
    return ctx.fleet.summary(fresh=True)


@router.get(
    "/fleet/history",
    tags=["fleet"],
    operation_id="getFleetHistory",
    summary="Fleet time series (hashrate, power, efficiency, temperatures...)",
    description="Metrics are summed (hashrate, power) or averaged/maxed as appropriate across miners. "
    "Add `:max`/`:min` to a metric for peaks (e.g. `temp_asic_c:max`). Valid metrics: " + ", ".join(mx.NAMES) + ".",
)
async def fleet_history(
    range: str = Query("24h", description="30m, 6h, 24h, 7d, 30d, 1y ..."),
    metrics: str = Query("hashrate_hs,power_w", description="Comma separated metric names"),
    step: int | None = Query(None, ge=1, description="Bucket size in seconds (default: automatic)"),
    start: float | None = None,
    end: float | None = None,
    per_device: bool = False,
    ctx: AppContext = Depends(get_ctx),
    _: Principal = Depends(require("read")),
) -> dict[str, Any]:
    s, e = window(range, start, end)
    try:
        h = await ctx.store.samples.history(metrics=csv_list(metrics), start=s, end=e, step=step, per_device=per_device)
    except ValueError as err:
        raise bad_request(str(err), "Valid metrics: " + ", ".join(mx.NAMES)) from err
    return h.as_dict()


# ------------------------------------------------------------------------------------------ devices


class AddDeviceBody(BaseModel):
    host: str = Field(description="IP address or host name, optionally with a port (192.168.1.50, bitaxe.local, 10.0.0.5:4028)")
    port: int | None = Field(None, ge=1, le=65535)
    name: str | None = Field(None, max_length=60)
    tags: list[str] = Field(default_factory=list)
    group: str | None = Field(None, max_length=40)


class UpdateDeviceBody(BaseModel):
    name: str | None = Field(None, max_length=60)
    tags: list[str] | None = None
    group: str | None = None
    notes: str | None = Field(None, max_length=2000)
    enabled: bool | None = None
    allow_control: bool | None = None
    poll_interval_s: float | None = Field(None, ge=2, le=3600)
    model_override: str | None = Field(None, max_length=60)
    host: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    power_override_w: float | None = Field(None, ge=0, le=20000, description="For miners that don't report power: watts at the wall")

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            required = {"name", "tags", "enabled", "allow_control", "host", "port"}
            if any(key in value and value[key] is None for key in required):
                raise ValueError("name, tags, enabled, allow_control, host and port cannot be null")
        return value


@router.get("/devices", tags=["devices"], operation_id="listDevices", summary="List monitored miners with live state")
async def list_devices(
    status: str | None = Query(None, description="online, degraded, offline, paused, unknown, disabled"),
    tag: str | None = None,
    q: str | None = Query(None, description="Search name, model, host"),
    ctx: AppContext = Depends(get_ctx),
    _: Principal = Depends(require("read")),
) -> list[DeviceView]:
    views = ctx.fleet.views()
    if status:
        wanted = {s.strip() for s in status.split(",")}
        views = [v for v in views if v.status.value in wanted]
    if tag:
        views = [v for v in views if tag in v.tags]
    if q:
        ql = q.lower()
        views = [v for v in views if ql in v.name.lower() or ql in v.display_model.lower() or ql in v.host.lower()]
    return views


@router.post(
    "/devices",
    tags=["devices"],
    operation_id="addDevice",
    summary="Add a miner by address (it is detected automatically)",
    description="Probes the address with every supported driver. If the same physical miner is already monitored (matched by MAC or chip serial) "
    "it is not added twice; the response says `created: false` and explains.",
)
async def add_device(body: AddDeviceBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    try:
        host, port = split_host_port(body.host, body.port)
    except ValueError as e:
        raise bad_request(str(e)) from e
    try:
        res = await ctx.fleet.add_by_host(host, port or body.port, name=body.name, tags=body.tags, group=body.group)
    except LookupError as e:
        raise ApiError(404, "no_miner_found", str(e), "Open the miner's own web page in a browser to confirm the address works.") from e
    view = ctx.fleet.view(res.device.id)
    if res.created:
        ctx.fleet.runtimes[res.device.id].wake.set()
    return {"created": res.created, "merged": res.merged, "note": res.note, "device": view}


@router.get("/devices/{device_id}", tags=["devices"], operation_id="getDevice", summary="One miner with its latest readings")
async def get_device(device_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> DeviceView:
    v = ctx.fleet.view(device_id)
    if v is None:
        raise not_found(f"Miner {device_id}", "List miners with GET /api/v1/devices.")
    return v


@router.patch("/devices/{device_id}", tags=["devices"], operation_id="updateDevice", summary="Rename, tag, enable/disable or re-address a miner")
async def update_device(device_id: str, body: UpdateDeviceBody, ctx: AppContext = Depends(get_ctx),
                        _: Principal = Depends(require("control"))) -> DeviceView:
    if ctx.fleet.view(device_id) is None:
        raise not_found(f"Miner {device_id}")
    await ctx.fleet.update(device_id, body.model_dump(exclude_unset=True))
    return ctx.fleet.view(device_id)  # type: ignore[return-value]


@router.delete("/devices/{device_id}", tags=["devices"], operation_id="removeDevice", summary="Stop monitoring a miner")
async def remove_device(device_id: str, keep_history: bool = False, ctx: AppContext = Depends(get_ctx),
                        _: Principal = Depends(require("control"))) -> dict[str, bool]:
    if not await ctx.fleet.remove(device_id, keep_history=keep_history):
        raise not_found(f"Miner {device_id}")
    return {"ok": True}


@router.post("/devices/{device_id}/poll", tags=["devices"], operation_id="pollDevice", summary="Read the miner right now")
async def poll_device(device_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> DeviceView:
    if ctx.fleet.view(device_id) is None:
        raise not_found(f"Miner {device_id}")
    return await ctx.fleet.poll_now(device_id)


@router.get("/devices/{device_id}/history", tags=["devices"], operation_id="getDeviceHistory", summary="Time series for one miner")
async def device_history(
    device_id: str,
    range: str = "24h",
    metrics: str = "hashrate_hs,temp_asic_c,power_w",
    step: int | None = Query(None, ge=1),
    start: float | None = None,
    end: float | None = None,
    ctx: AppContext = Depends(get_ctx),
    _: Principal = Depends(require("read")),
) -> dict[str, Any]:
    if ctx.fleet.view(device_id) is None:
        raise not_found(f"Miner {device_id}")
    s, e = window(range, start, end)
    try:
        h = await ctx.store.samples.history(metrics=csv_list(metrics), start=s, end=e, step=step, device_ids=[device_id], per_device=True)
    except ValueError as err:
        raise bad_request(str(err), "Valid metrics: " + ", ".join(mx.NAMES)) from err
    series = h.devices.get(device_id, {csv_list(metrics)[0]: [None] * len(h.t)})
    return {"step": h.step, "source": h.source, "t": h.t, "series": series}


@router.get("/devices/{device_id}/raw", tags=["devices"], operation_id="getDeviceRaw",
            summary="The unprocessed reply from the miner (for debugging and bug reports)")
async def device_raw(device_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    rt = ctx.fleet.runtimes.get(device_id)
    if rt is None:
        raise not_found(f"Miner {device_id}")
    raw = rt.driver.last_raw if rt.driver else None
    if isinstance(raw, dict):  # hide wifi name / mac-like identifiers? keep: it is the user's own data, but drop obvious secrets
        raw = {k: v for k, v in raw.items() if "pass" not in k.lower()}
    return {"driver": rt.device.driver, "raw": raw}


@router.get("/devices/{device_id}/tuning", tags=["devices"], operation_id="getDeviceTuning",
            summary="Safe frequency/voltage choices the miner itself allows, and what is set now")
async def device_tuning(device_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    rt = ctx.fleet.runtimes.get(device_id)
    if rt is None:
        raise not_found(f"Miner {device_id}")
    t = rt.telemetry
    opts = None
    try:
        if rt.driver is None:
            from bsmm.drivers.registry import driver_for

            rt.driver = driver_for(rt.device, ctx.http, timeout=ctx.settings.current.polling.timeout_s)
        opts = await rt.driver.tuning_options()
    except Exception:  # an unreachable miner simply has no options to show
        opts = None
    return {
        "allowed": bool(opts and opts.frequency_mhz and opts.core_voltage_mv) and ctx.settings.current.safety.allow_tuning,
        "tuning_enabled_in_settings": ctx.settings.current.safety.allow_tuning,
        "options": None if opts is None else {
            "frequency_mhz": opts.frequency_mhz, "core_voltage_mv": opts.core_voltage_mv,
            "default_frequency_mhz": opts.default_frequency_mhz, "default_core_voltage_mv": opts.default_core_voltage_mv,
            "max_power_w": opts.max_power_w, "max_temp_c": opts.max_temp_c,
        },
        "current": None if t is None else {"frequency_mhz": t.frequency_mhz, "core_voltage_mv": t.core_voltage_mv,
                                           "power_w": t.power_w, "hashrate_hs": t.hashrate_hs, "efficiency_j_th": t.efficiency_j_th,
                                           "temp_asic_c": t.temp_asic_c},
    }


class ActionBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters, e.g. {url, port, user, password, role} for set_pool")
    dry_run: bool = Field(False, description="Validate parameters (may read safe tuning ranges) without writing to the miner or audit log; identity is rechecked on execution")


ACTION_DOC = (
    "Actions: `restart`, `identify` (flash the screen/LED), `pause`, `resume`, `set_pool` {url, port, user, password?, role: primary|fallback, tls?}, "
    "`set_fan` {auto?, speed_pct?, temp_target_c?}, `set_tuning` {frequency_mhz?, core_voltage_mv?} (values must be ones the miner lists, and tuning must be enabled in Settings > Safety). "
    "Every action is audited."
)


@router.post("/devices/{device_id}/actions/{action}", tags=["devices"], operation_id="runDeviceAction", summary="Control a miner", description=ACTION_DOC)
async def run_action(device_id: str, action: str, request: Request, body: ActionBody | None = None, ctx: AppContext = Depends(get_ctx),
                     principal: Principal = Depends(require("control"))) -> dict[str, Any]:
    if ctx.fleet.view(device_id) is None:
        raise not_found(f"Miner {device_id}")
    body = body or ActionBody()
    return await ctx.fleet.run_action(device_id, action, body.params, actor=principal.name, dry_run=body.dry_run)


class BulkBody(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    device_ids: list[str] | None = Field(None, description="Specific miners; omit to use `tag` or `all`")
    tag: str | None = None
    all: bool = False
    dry_run: bool = True  # bulk operations preview by default; send dry_run=false to apply


@router.post("/devices/actions", tags=["devices"], operation_id="runBulkAction",
             summary="Run one action on many miners (previews by default)", description=ACTION_DOC + " **Bulk requests default to `dry_run: true`.**")
async def bulk_action(body: BulkBody, ctx: AppContext = Depends(get_ctx), principal: Principal = Depends(require("control"))) -> dict[str, Any]:
    if body.device_ids:
        ids = body.device_ids
    elif body.tag:
        ids = [v.id for v in ctx.fleet.views() if body.tag in v.tags]
    elif body.all:
        ids = [v.id for v in ctx.fleet.views() if v.status != DeviceStatus.DISABLED]
    else:
        raise bad_request("Say which miners: device_ids, a tag, or all=true.")
    results = []
    for did in ids:
        v = ctx.fleet.view(did)
        if v is None:
            results.append({"device_id": did, "ok": False, "error": "unknown miner"})
            continue
        try:
            r = await ctx.fleet.run_action(did, body.action, body.params, actor=principal.name, dry_run=body.dry_run)
            results.append({"device_id": did, "name": v.name, **r})
        except Exception as e:  # report per miner, never abort the batch
            results.append({"device_id": did, "name": v.name, "ok": False, "error": str(e)})
    return {"dry_run": body.dry_run, "results": results, "ok": all(r.get("ok") for r in results)}


@router.get("/devices/{device_id}/audit", tags=["devices"], operation_id="getDeviceAudit", summary="Who changed what on this miner")
async def device_audit(device_id: str, limit: int = Query(50, ge=1, le=500), ctx: AppContext = Depends(get_ctx),
                       _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"audit": await ctx.store.list_audit(limit, device_id)}


# ------------------------------------------------------------------------------------------ discovery


class DiscoveryBody(BaseModel):
    cidrs: list[str] | None = Field(None, description="Networks to scan, e.g. ['192.168.1.0/24']. Default: the networks this computer is on.")
    ports: list[int] | None = Field(None, description="Extra TCP ports to check besides 80 and 4028")
    include_sources: bool = Field(True, description="Also look for your Bitcoin node / pool")


@router.get("/discovery/suggest", tags=["discovery"], operation_id="suggestScanRanges", summary="Networks worth scanning")
async def suggest(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"cidrs": ctx.discovery.suggest_cidrs()}


@router.post("/discovery", tags=["discovery"], operation_id="startDiscovery", summary="Scan the network for miners (and your node/pool)",
             description="Returns immediately with a job id. Poll GET /discovery/{id} or watch the `discovery` events on the stream. Only private address ranges can be scanned.")
async def start_discovery(body: DiscoveryBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    try:
        job = ctx.discovery.start(body.cidrs, include_sources=body.include_sources, ports=body.ports)
    except ValueError as e:
        raise bad_request(str(e)) from e
    return job.as_dict()


@router.get("/discovery/{job_id}", tags=["discovery"], operation_id="getDiscovery", summary="Scan progress and results")
async def get_discovery(job_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    job = ctx.discovery.jobs.get(job_id)
    if job is None:
        raise not_found("That scan")
    return job.as_dict()


@router.delete("/discovery/{job_id}", tags=["discovery"], operation_id="cancelDiscovery", summary="Stop a running scan")
async def cancel_discovery(job_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, bool]:
    return {"ok": ctx.discovery.cancel(job_id)}


class AdoptBody(BaseModel):
    keys: list[str] | None = Field(None, description="'host:port' of the found miners to add. Omit to add every new, non-duplicate one.")
    tags: list[str] = Field(default_factory=list)


@router.post("/discovery/{job_id}/adopt", tags=["discovery"], operation_id="adoptDiscovered", summary="Start monitoring the miners a scan found")
async def adopt(job_id: str, body: AdoptBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    try:
        results = await ctx.discovery.adopt(job_id, body.keys, tags=body.tags)
    except KeyError as e:
        raise not_found("That scan") from e
    for r in results:
        if r.created:
            ctx.fleet.runtimes[r.device.id].wake.set()
    return {"added": [ctx.fleet.view(r.device.id) for r in results if r.created],
            "merged": [{"device": r.device.name, "note": r.note} for r in results if not r.created]}


# ------------------------------------------------------------------------------------------ live stream

TOPICS = {"device", "device_removed", "fleet", "event", "network", "alerts", "discovery", "block_found", "new_block"}


@router.get(
    "/stream",
    tags=["fleet"],
    operation_id="streamEvents",
    summary="Live updates (Server-Sent Events)",
    description="`GET /api/v1/stream?topics=device,fleet,event` keeps the connection open and pushes JSON events. "
    "Topics: " + ", ".join(sorted(TOPICS)) + ". Works with curl (`curl -N`), browsers (EventSource) and any SSE library.",
    response_class=StreamingResponse,
)
async def stream(request: Request, topics: str | None = Query(None, description="Comma separated; default: all"),
                 ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> StreamingResponse:
    wanted = set(csv_list(topics)) & TOPICS if topics else set(TOPICS)
    if topics and not wanted:
        raise bad_request(f"No valid topics. Choose from: {', '.join(sorted(TOPICS))}")
    sub = ctx.bus.subscribe(wanted, maxsize=1024)

    async def gen() -> AsyncIterator[bytes]:
        from bsmm.api.deps import _bearer, resolve_principal

        # Re-read credentials/policy before each event and at most one second after an idle revoke.
        recheck_interval_s = 1.0

        async def authorized() -> bool:
            creds = await _bearer(request)
            current = await resolve_principal(request, creds)
            # A revoked credential must not fall back to a different ambient principal.
            return current is not None and current == _ and current.allows("read")

        try:
            if not await authorized():
                return
            hello = {"version": ctx.settings.current.general.instance_name, "topics": sorted(wanted)}
            yield f"event: hello\ndata: {json.dumps(hello)}\n\n".encode()
            if "fleet" in wanted:
                if not await authorized():
                    return
                yield f"event: fleet\ndata: {ctx.fleet.summary().model_dump_json()}\n\n".encode()
            while True:
                if await request.is_disconnected():
                    break
                msg = await sub.get(timeout=recheck_interval_s)
                if not await authorized():
                    break
                if msg is None:
                    yield b": ping\n\n"
                    continue
                yield f"event: {msg.topic}\nid: {msg.seq}\ndata: {json.dumps(msg.data, default=str)}\n\n".encode()
        except asyncio.CancelledError:
            pass
        finally:
            sub.close()

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
