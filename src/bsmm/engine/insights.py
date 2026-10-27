"""Plain-language observations and suggestions, derived by rules (no LLM, no guessing).

Each insight is small, concrete and says what to do about it. The UI shows them as cards; agents
get the same list from ``GET /api/v1/insights`` so they can advise the user.
"""

from __future__ import annotations

import statistics
from typing import Any

from bsmm.context import AppContext
from bsmm.models import DeviceStatus
from bsmm.units import format_percent, format_si

DISMISSED_KEY = "insights.dismissed"


def _i(id_: str, level: str, title: str, body: str, *, action: dict[str, Any] | None = None, device_id: str | None = None) -> dict[str, Any]:
    return {"id": id_, "level": level, "title": title, "body": body, "action": action, "device_id": device_id}


async def build_insights(ctx: AppContext) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    views = ctx.fleet.views()
    s = ctx.settings.current
    net = ctx.network.state
    summary = ctx.fleet.summary(fresh=True)

    if not views:
        out.append(_i("no-miners", "tip", "Find your miners", "No miners are being monitored yet. A scan of your network takes about 20 seconds.",
                      action={"label": "Scan my network", "type": "route", "target": "/setup"}))

    # sources
    have_node = any(h.kind in ("bitcoin_core", "public_pool", "ckpool") and not h.implicit for h in net.sources)
    if views and not have_node:
        out.append(_i("no-node", "tip", "Connect your node or pool",
                      "Adding your Bitcoin node or solo pool unlocks block detection, pool statistics and your own, private network data.",
                      action={"label": "Add a node or pool", "type": "route", "target": "/settings/sources"}))
    if views and not net.available:
        out.append(_i("no-network", "warning", "Network data is missing",
                      "Without the current difficulty the app cannot work out your odds. Allow public data (mempool.space) or connect a node.",
                      action={"label": "Open data sources", "type": "route", "target": "/settings/sources"}))
    if net.node and net.node.reachable and not net.node.synced:
        out.append(_i("node-syncing", "warning", "Your node is still syncing",
                      f"It is at block {net.node.blocks:,} of {net.node.headers:,}. Mining against an unsynced node can waste work on stale blocks."
                      if net.node.blocks and net.node.headers else "Mining against an unsynced node can waste work on stale blocks."))
    if net.node_behind_by and net.node_behind_by > 3:
        out.append(_i("node-behind", "warning", f"Your node is {net.node_behind_by} blocks behind", "Check that it has peers and is not busy catching up."))

    # notifications & security
    if views and not [c for c in await ctx.store.list_channels() if c.enabled]:
        out.append(_i("no-channel", "tip", "Get alerts on your phone",
                      "You'll see problems on this dashboard, but a notification (ntfy, Telegram, Discord or email) tells you when you are away.",
                      action={"label": "Set up notifications", "type": "route", "target": "/settings/notifications"}))
    if s.auth.mode == "none" and views and ctx.config.host not in ("127.0.0.1", "localhost"):
        out.append(_i("no-password", "tip", "Protect the dashboard with a password",
                      "Anyone on your network can open this page and restart your miners. A password (or token) takes ten seconds to set.",
                      action={"label": "Set a password", "type": "route", "target": "/settings/security"}))
    if abs(s.energy.price_per_kwh - 0.12) < 1e-9 and views and not await ctx.store.kv_get("insight.energy_confirmed", False):
        out.append(_i("energy-default", "tip", "Set your electricity price",
                      "Costs and break-even figures assume 0.12 per kWh until you enter your own rate.",
                      action={"label": "Set price", "type": "route", "target": "/settings/energy"}))

    # per-device observations
    eff_by_family: dict[str, list[float]] = {}
    for v in views:
        t = v.telemetry
        if t and t.efficiency_j_th and v.status in (DeviceStatus.ONLINE, DeviceStatus.DEGRADED):
            eff_by_family.setdefault(v.family, []).append(t.efficiency_j_th)
    for v in views:
        t = v.telemetry
        if v.alt_hosts:
            out.append(_i(f"alt-hosts-{v.id}", "info", f"{v.name} answers on {1 + len(v.alt_hosts)} addresses",
                          f"It is reachable on {', '.join([v.host, *v.alt_hosts])}. That's one miner, and it is only counted once.", device_id=v.id))
        if not t or v.status == DeviceStatus.OFFLINE:
            continue
        if t.wifi_rssi_dbm is not None and t.wifi_rssi_dbm <= -78:
            out.append(_i(f"wifi-{v.id}", "tip", f"{v.name} has a weak WiFi signal ({t.wifi_rssi_dbm:.0f} dBm)",
                          "Weak WiFi causes rejected shares and dropouts. Move it closer to the router or add an access point nearby.", device_id=v.id))
        if t.free_heap_bytes is not None and 0 < t.free_heap_bytes < 30_000 and v.family not in ("avalon", "antminer"):
            out.append(_i(f"heap-{v.id}", "info", f"{v.name} is low on memory", f"{t.free_heap_bytes / 1000:.0f} kB free. If it gets slower over time, a restart helps.", device_id=v.id))
        peers = eff_by_family.get(v.family, [])
        if t.efficiency_j_th and len(peers) >= 3:
            med = statistics.median(peers)
            if t.efficiency_j_th > med * 1.35:
                out.append(_i(f"eff-{v.id}", "tip", f"{v.name} is less efficient than similar miners",
                              f"{t.efficiency_j_th:.1f} J/TH versus {med:.1f} J/TH typical for your {v.family} miners. Check cooling, voltage and frequency.", device_id=v.id))
        if t.reject_rate_pct is not None and (t.shares_accepted or 0) > 500 and t.reject_rate_pct > 2:
            out.append(_i(f"reject-{v.id}", "tip", f"{v.name} rejects {t.reject_rate_pct:.1f}% of its shares",
                          "A little is normal; sustained rejects usually mean a weak network link or a pool/node that is slow to hand out work.", device_id=v.id))

    # payout addresses
    if len(summary.addresses) > 1:
        out.append(_i("multi-address", "info", f"Your miners pay {len(summary.addresses)} different addresses",
                      "That's fine if it is intentional. If not, point every miner at the same payout address so a block would pay one wallet."))

    # fun, honest progress
    if summary.best_diff and net.difficulty:
        out.append(_i("best-share", "info", "How close have you come?",
                      f"Your best share ({format_si(summary.best_diff)}) reached {format_percent(summary.best_diff / net.difficulty, 4)} of the way to a block. "
                      "Shares are what prove you are hashing; one of them just has to be big enough, and any hash could be the one."))

    dismissed = set(await ctx.store.kv_get(DISMISSED_KEY, []))
    return [i for i in out if i["id"] not in dismissed]


async def dismiss(ctx: AppContext, insight_id: str) -> None:
    dismissed = set(await ctx.store.kv_get(DISMISSED_KEY, []))
    dismissed.add(insight_id)
    await ctx.store.kv_set(DISMISSED_KEY, sorted(dismissed))
