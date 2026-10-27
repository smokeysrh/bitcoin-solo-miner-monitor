"""Alert rules, notification channels and the activity log."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from bsmm.api.deps import get_ctx, require
from bsmm.api.errors import bad_request, not_found
from bsmm.auth import Principal
from bsmm.context import AppContext
from bsmm.engine.alerts import RULE_SPECS
from bsmm.models import Channel, Severity
from bsmm.notify.channels import CHANNEL_CLASSES, Notification
from bsmm.storage.store import new_id

router = APIRouter()


# ------------------------------------------------------------------------------------------ events


@router.get("/events", tags=["alerts"], operation_id="listEvents", summary="The activity log: restarts, new best shares, outages, blocks...")
async def list_events(
    limit: int = Query(50, ge=1, le=500),
    before_id: int | None = Query(None, description="Page backwards: only events older than this id"),
    type: str | None = Query(None, description="One or more event types, comma separated"),
    device_id: str | None = None,
    min_severity: Severity | None = None,
    unacked: bool = False,
    since: float | None = None,
    ctx: AppContext = Depends(get_ctx),
    _: Principal = Depends(require("read")),
) -> dict[str, Any]:
    types = [t.strip() for t in type.split(",")] if type else None
    events = await ctx.store.list_events(limit=limit, before_id=before_id, types=types, device_id=device_id,
                                         min_severity=min_severity, unacked_only=unacked, since=since)
    return {"events": [e.model_dump(mode="json") for e in events], "next_before_id": events[-1].id if len(events) == limit else None}


@router.post("/events/{event_id}/ack", tags=["alerts"], operation_id="ackEvent", summary="Mark an event as seen")
async def ack_event(event_id: int, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, bool]:
    return {"ok": await ctx.store.ack_event(event_id)}


@router.post("/events/ack-all", tags=["alerts"], operation_id="ackAllEvents", summary="Mark every event as seen")
async def ack_all(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, int]:
    return {"acknowledged": await ctx.store.ack_all_events()}


# ------------------------------------------------------------------------------------------ rules


class RuleBody(BaseModel):
    kind: str = Field(description="One of GET /alerts/rule-types")
    name: str | None = Field(None, max_length=80)
    enabled: bool = True
    severity: Severity | None = None
    scope: dict[str, Any] | None = Field(None, description='{"all": true} | {"device_ids": [...]} | {"tags": [...]}')
    params: dict[str, Any] = Field(default_factory=dict)
    channel_ids: list[str] = Field(default_factory=list, description="Empty = every enabled channel")
    cooldown_s: float | None = Field(None, ge=0)


class RulePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    severity: Severity | None = None
    scope: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    channel_ids: list[str] | None = None
    cooldown_s: float | None = Field(None, ge=0)


@router.get("/alerts/rule-types", tags=["alerts"], operation_id="listRuleTypes", summary="The kinds of alert you can create, with their settings")
async def rule_types(_: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"rule_types": [s.as_dict() for s in RULE_SPECS.values()]}


@router.get("/alerts/rules", tags=["alerts"], operation_id="listAlertRules", summary="Your alert rules")
async def list_rules(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"rules": [r.model_dump(mode="json") for r in await ctx.store.list_rules()]}


@router.post("/alerts/rules", tags=["alerts"], operation_id="createAlertRule", summary="Create an alert rule (admin)")
async def create_rule(body: RuleBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    data = body.model_dump(exclude_none=True)
    try:
        rule = await ctx.alerts.create_rule(data)
    except ValueError as e:
        raise bad_request(str(e)) from e
    return {"rule": rule.model_dump(mode="json")}


@router.patch("/alerts/rules/{rule_id}", tags=["alerts"], operation_id="updateAlertRule", summary="Change an alert rule (admin)")
async def patch_rule(rule_id: str, body: RulePatch, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    try:
        rule = await ctx.alerts.update_rule(rule_id, body.model_dump(exclude_unset=True))
    except KeyError as e:
        raise not_found("That rule") from e
    except ValueError as e:
        raise bad_request(str(e)) from e
    return {"rule": rule.model_dump(mode="json")}


@router.delete("/alerts/rules/{rule_id}", tags=["alerts"], operation_id="deleteAlertRule", summary="Delete a custom rule (built-in rules can only be switched off)")
async def delete_rule(rule_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, bool]:
    rule = await ctx.store.get_rule(rule_id)
    if rule is None:
        raise not_found("That rule")
    if rule.builtin:
        raise bad_request("Built-in rules can't be deleted, only switched off.", f"PATCH /api/v1/alerts/rules/{rule_id} with {{\"enabled\": false}}")
    await ctx.store.delete_rule(rule_id)
    return {"ok": True}


@router.get("/alerts/active", tags=["alerts"], operation_id="listActiveAlerts", summary="Problems that are happening right now")
async def active_alerts(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"active": ctx.alerts.active_alerts()}


# ------------------------------------------------------------------------------------------ channels


class ChannelBody(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=60)
    config: dict[str, Any] = Field(default_factory=dict, description="Non-secret fields (chat_id, topic, server...)")
    secret: dict[str, str] = Field(default_factory=dict, description="Write-only fields (tokens, webhook URLs, passwords)")
    enabled: bool = True
    min_severity: Severity = Severity.INFO


class ChannelPatch(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    secret: dict[str, str] | None = Field(None, description="Replace secrets; omit to keep; {} to clear")
    enabled: bool | None = None
    min_severity: Severity | None = None


def _split_fields(kind: str, config: dict[str, Any], secret: dict[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
    """Whatever the caller sent, secret fields always end up in the encrypted store."""
    cls = CHANNEL_CLASSES[kind]
    secret_names = {f.name for f in cls.fields if f.secret}
    cfg = {k: v for k, v in config.items() if k not in secret_names}
    sec = dict(secret)
    for k, v in config.items():
        if k in secret_names and v not in (None, ""):
            sec[k] = str(v)
    return cfg, sec


def _check_kind(kind: str) -> None:
    if kind not in CHANNEL_CLASSES:
        raise bad_request(f"Unknown channel type {kind!r}.", "Valid: " + ", ".join(CHANNEL_CLASSES))


@router.get("/notifications/channel-types", tags=["notifications"], operation_id="listChannelTypes",
            summary="Where notifications can go, and exactly which fields each needs")
async def channel_types(_: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"channel_types": [c.describe() for c in CHANNEL_CLASSES.values()]}


@router.get("/notifications/channels", tags=["notifications"], operation_id="listChannels", summary="Your notification channels (secrets are never shown)")
async def list_channels(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"channels": [c.model_dump(mode="json") for c in await ctx.store.list_channels()]}


@router.post("/notifications/channels", tags=["notifications"], operation_id="createChannel", summary="Add a notification channel (admin)")
async def create_channel(body: ChannelBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    _check_kind(body.kind)
    cfg, sec = _split_fields(body.kind, body.config, body.secret)
    ch = Channel(id=new_id("ch"), kind=body.kind, name=body.name, enabled=body.enabled, config=cfg, min_severity=body.min_severity)
    await ctx.store.save_channel(ch, secret=sec)
    return {"channel": (await ctx.store.get_channel(ch.id)).model_dump(mode="json")}  # type: ignore[union-attr]


@router.patch("/notifications/channels/{channel_id}", tags=["notifications"], operation_id="updateChannel", summary="Edit a channel (admin)")
async def patch_channel(channel_id: str, body: ChannelPatch, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    ch = await ctx.store.get_channel(channel_id)
    if ch is None:
        raise not_found("That channel")
    data = body.model_dump(exclude_unset=True)
    secret = data.get("secret")
    if "config" in data and data["config"] is not None:
        cfg, sec = _split_fields(ch.kind, data["config"], secret or {})
        ch.config = cfg
        secret = sec if (sec or secret is not None) else None
    for k in ("name", "enabled", "min_severity"):
        if k in data and data[k] is not None:
            setattr(ch, k, data[k])
    await ctx.store.save_channel(ch, secret=secret)
    return {"channel": (await ctx.store.get_channel(channel_id)).model_dump(mode="json")}  # type: ignore[union-attr]


@router.delete("/notifications/channels/{channel_id}", tags=["notifications"], operation_id="deleteChannel", summary="Remove a channel (admin)")
async def delete_channel(channel_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, bool]:
    if not await ctx.store.delete_channel(channel_id):
        raise not_found("That channel")
    return {"ok": True}


@router.post("/notifications/channels/{channel_id}/test", tags=["notifications"], operation_id="testChannel", summary="Send a test message through a saved channel")
async def test_channel(channel_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    try:
        res = await ctx.notifier.send_test(channel_id)
    except KeyError as e:
        raise not_found("That channel") from e
    return res.as_dict()


@router.post("/notifications/test", tags=["notifications"], operation_id="testChannelInline", summary="Try channel settings without saving them")
async def test_inline(body: ChannelBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    _check_kind(body.kind)
    cfg, sec = _split_fields(body.kind, body.config, body.secret)
    return (await ctx.notifier.send_test_inline(body.kind, cfg, sec)).as_dict()


@router.post("/notifications/send", tags=["notifications"], operation_id="sendNotification", summary="Send a custom message to your channels (handy for agents)")
async def send_custom(title: str = Query(..., max_length=200), body: str = Query("", max_length=2000), severity: Severity = Severity.INFO,
                      ctx: AppContext = Depends(get_ctx), principal: Principal = Depends(require("control"))) -> dict[str, Any]:
    n = Notification(title=title, body=body, severity=severity, type="custom", data={"sent_by": principal.name}, ts=time.time())
    results = await ctx.notifier.dispatch(n)
    await ctx.events.emit("custom_notification", title, severity=severity, body=body or None, data={"sent_by": principal.name})
    return {"results": [r.as_dict() for r in results]}
