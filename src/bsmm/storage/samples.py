"""Time-series storage: raw samples, rollups (1m / 1h / 1d), retention and history queries."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from bsmm.models import Telemetry
from bsmm.storage import metrics as mx
from bsmm.storage.db import Database

_RAW_COLS = ", ".join(mx.NAMES)
_RAW_INSERT = (
    f"INSERT OR REPLACE INTO samples (device_id, ts, {_RAW_COLS}) "
    f"VALUES (:device_id, :ts, {', '.join(':' + n for n in mx.NAMES)})"
)


@dataclass(slots=True)
class Retention:
    raw_days: float = 2
    minute_days: float = 90
    hour_days: float = 730
    day_days: float | None = None  # forever


@dataclass(slots=True)
class History:
    step: int
    source: str
    t: list[int] = field(default_factory=list)
    series: dict[str, list[float | None]] = field(default_factory=dict)
    devices: dict[str, dict[str, list[float | None]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"step": self.step, "source": self.source, "t": self.t, "series": self.series}
        if self.devices:
            out["devices"] = self.devices
        if self.warnings:
            out["warnings"] = self.warnings
        return out


def telemetry_to_row(device_id: str, t: Telemetry) -> dict[str, Any]:
    row: dict[str, Any] = {"device_id": device_id, "ts": int(t.ts)}
    for name in mx.NAMES:
        if name == "online":
            row[name] = 1.0 if t.online else 0.0
            continue
        v = getattr(t, name, None)
        row[name] = float(v) if isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) else None
    return row


def parse_metric_spec(spec: str) -> tuple[str, str]:
    """``"temp_asic_c:max"`` -> ("temp_asic_c", "max"). Default aggregation is avg (max for counters)."""
    name, _, agg = spec.partition(":")
    if name not in mx.BY_NAME:
        raise ValueError(f"unknown metric {name!r}")
    m = mx.BY_NAME[name]
    agg = agg or ("max" if m.kind == "counter" else "avg")
    if agg not in {"avg", "min", "max"}:
        raise ValueError(f"unknown aggregation {agg!r}")
    if agg == "min" and not m.keep_min:
        agg = "avg"
    if agg == "max" and m.kind != "counter" and not m.keep_max:
        agg = "avg"
    return name, agg


class SampleStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    # -- writing ------------------------------------------------------------------------------

    async def write(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        async with self.db.tx() as conn:
            await conn.executemany(_RAW_INSERT, rows)
        lo = min(r["ts"] for r in rows)
        hi = max(r["ts"] for r in rows)
        await self.rollup_window(lo, hi + 1)

    async def rollup_window(self, t0: int, t1: int) -> None:
        """Recompute every rollup bucket that overlaps [t0, t1). Safe to call repeatedly."""
        async with self.db.tx() as conn:
            for target, bucket_s, source in mx.LEVELS:
                lo = (int(t0) // bucket_s) * bucket_s
                hi = -(-int(t1) // bucket_s) * bucket_s
                await conn.execute(mx.rollup_sql(target, bucket_s, source), {"t0": lo, "t1": hi})

    async def rebuild_rollups(self) -> None:
        """Recompute all rollups from raw data (maintenance / after restoring a backup)."""
        row = await self.db.fetchone("SELECT MIN(ts) AS lo, MAX(ts) AS hi FROM samples")
        if row and row["lo"] is not None:
            await self.rollup_window(int(row["lo"]), int(row["hi"]) + 1)

    async def insert_rollup_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Direct rollup insert (used to backfill demo history).

        Rows may omit metric columns (an offline bucket has no hashrate); they are stored as NULL.
        Unknown keys are an error rather than being interpolated into SQL.
        """
        if table not in {t for t, _, _ in mx.LEVELS} or not rows:
            raise ValueError("bad rollup table")
        cols = ["device_id", "bucket", "n", *(c for m in mx.METRICS for c in mx.rollup_columns(m))]
        known = set(cols)
        for r in rows:
            extra = set(r) - known
            if extra:
                raise ValueError(f"unknown rollup column(s): {', '.join(sorted(extra))}")
        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        async with self.db.tx() as conn:
            await conn.executemany(sql, [{c: r.get(c) for c in cols} for r in rows])

    async def prune(self, retention: Retention, now: float | None = None) -> dict[str, int]:
        now = now if now is not None else time.time()
        deleted: dict[str, int] = {}
        plan = [
            ("samples", "ts", retention.raw_days),
            ("samples_1m", "bucket", retention.minute_days),
            ("samples_1h", "bucket", retention.hour_days),
            ("samples_1d", "bucket", retention.day_days),
        ]
        async with self.db.tx() as conn:
            for table, col, days in plan:
                if days is None:
                    continue
                cur = await conn.execute(f"DELETE FROM {table} WHERE {col} < ?", (int(now - days * 86400),))
                deleted[table] = cur.rowcount
        return deleted

    async def delete_device_samples(self, device_id: str) -> None:
        async with self.db.tx() as conn:
            for table in ("samples", "samples_1m", "samples_1h", "samples_1d"):
                await conn.execute(f"DELETE FROM {table} WHERE device_id = ?", (device_id,))

    # -- reading ------------------------------------------------------------------------------

    @staticmethod
    def pick_source(span_s: float) -> tuple[str, int]:
        """(table, native bucket seconds) for a time span."""
        if span_s <= 2 * 3600:
            return "samples", 1
        if span_s <= 3 * 86400:
            return "samples_1m", 60
        if span_s <= 120 * 86400:
            return "samples_1h", 3600
        return "samples_1d", 86400

    async def history(
        self,
        *,
        metrics: list[str],
        start: float,
        end: float | None = None,
        step: int | None = None,
        device_ids: list[str] | None = None,
        per_device: bool = False,
    ) -> History:
        end = end if end is not None else time.time()
        if end <= start:
            raise ValueError("end must be after start")
        specs = [parse_metric_spec(s) for s in metrics]
        if not specs:
            raise ValueError("pick at least one metric")
        want_eff = any(n == "efficiency_j_th" for n, _ in specs)
        # efficiency for a fleet is total power / total hashrate, not a mean of ratios
        fetch: list[tuple[str, str]] = list(specs)
        if want_eff and not per_device:
            for need in ("power_w", "hashrate_hs"):
                if (need, "avg") not in fetch:
                    fetch.append((need, "avg"))

        span = end - start
        table, native = self.pick_source(span)
        # Choose a retained tier covering the oldest requested data, not just the
        # window's duration. This also avoids blank/partial zooms across pruning edges.
        tiers = [("samples", 1, "ts"), *((t, s, "bucket") for t, s, _ in mx.LEVELS)]
        chosen = next(i for i, (t, _, _) in enumerate(tiers) if t == table)
        bounds: dict[str, int | None] = {}
        device_filter = f" AND device_id IN ({', '.join('?' for _ in device_ids)})" if device_ids else ""
        for tier, size, col in tiers:
            params_bounds: list[Any] = [int(start) // size * size, int(end)]
            if device_ids:
                params_bounds.extend(device_ids)
            bounds[tier] = await self.db.scalar(f"SELECT MIN({col}) FROM {tier} WHERE {col} >= ? AND {col} <= ?{device_filter}", params_bounds)
        present = [i for i in range(chosen, len(tiers)) if bounds[tiers[i][0]] is not None]
        if present:
            chosen = present[0]
            for i in present[1:]:
                current_start = bounds[tiers[chosen][0]]
                older_start = bounds[tiers[i][0]]
                assert current_start is not None and older_start is not None
                if older_start < current_start // tiers[i][1] * tiers[i][1]:
                    chosen = i
                elif older_start <= start < current_start:
                    # Pruning can cut *inside* the same coarse bucket. Compare
                    # represented observations, not just rounded timestamps; simple
                    # alignment alone would incorrectly coarsen every sparse live chart.
                    finer, _, finer_col = tiers[chosen]
                    count = "COUNT(*)" if finer == "samples" else "COALESCE(SUM(n), 0)"
                    retained_n = await self.db.scalar(
                        f"SELECT COALESCE(SUM(n), 0) FROM {tiers[i][0]} WHERE bucket = ?{device_filter}",
                        [older_start, *(device_ids or [])])
                    finer_n = await self.db.scalar(
                        f"SELECT {count} FROM {finer} WHERE {finer_col} >= ? AND {finer_col} < ?{device_filter}",
                        [older_start, older_start + tiers[i][1], *(device_ids or [])])
                    if retained_n > finer_n:
                        chosen = i
            table, native, _ = tiers[chosen]
        if step is None:
            step = max(native, int(span / 400))
        step = max(native, int(step))
        if table != "samples":
            step = max(native, (step // native) * native)

        ts_col = "ts" if table == "samples" else "bucket"
        select: list[str] = []
        for name, agg in fetch:
            m = mx.BY_NAME[name]
            alias = f"{name}__{agg}"
            if table == "samples":
                fn = {"avg": "AVG", "min": "MIN", "max": "MAX"}[agg]
                select.append(f"{fn}({name}) AS {alias}")
            elif agg == "avg":
                if m.kind == "counter":
                    select.append(f"AVG({name}) AS {alias}")
                else:
                    select.append(f"{mx.weighted_avg(name)} AS {alias}")
                    select.append(f"MAX(CASE WHEN {name} IS NOT NULL AND {name}_n IS NULL THEN 1 ELSE 0 END) AS {name}__legacy")
            elif agg == "min":
                select.append(f"MIN({name}_min) AS {alias}")
            else:
                col = name if m.kind == "counter" else f"{name}_max"
                select.append(f"MAX({col}) AS {alias}")
        where = f"{ts_col} >= :start AND {ts_col} <= :end"  # inclusive: the newest sample is part of "now"
        params: dict[str, Any] = {"start": int(start) // native * native, "end": int(end), "step": step}
        if device_ids:
            ph = []
            for i, d in enumerate(device_ids):
                params[f"d{i}"] = d
                ph.append(f":d{i}")
            where += f" AND device_id IN ({', '.join(ph)})"
        sql = (
            f"SELECT device_id, ({ts_col} / :step) * :step AS b, {', '.join(select)} FROM {table} "
            f"WHERE {where} GROUP BY device_id, b ORDER BY b"
        )
        rows = await self.db.fetchall(sql, params)

        first = (int(start) // step) * step
        buckets = list(range(first, int(end) + 1, step))
        index = {b: i for i, b in enumerate(buckets)}
        out = History(step=step, source=table, t=buckets)
        if table != "samples" and any(r[f"{n}__legacy"] for r in rows for n, a in fetch
                                      if a == "avg" and mx.BY_NAME[n].kind != "counter"):
            out.warnings.append("Legacy rollups have unknown per-metric counts; averages including them are approximate.")

        per: dict[str, dict[str, list[float | None]]] = {}
        for r in rows:
            slot = index.get(r["b"])
            if slot is None:
                continue
            i = slot
            dev = per.setdefault(r["device_id"], {f"{n}__{a}": [None] * len(buckets) for n, a in fetch})
            for n, a in fetch:
                v = r[f"{n}__{a}"]
                dev[f"{n}__{a}"][i] = float(v) if v is not None else None

        label = {(n, a): (n if a == ("max" if mx.BY_NAME[n].kind == "counter" else "avg") else f"{n}:{a}") for n, a in specs}
        if per_device:
            for dev_id, cols in per.items():
                out.devices[dev_id] = {label[(n, a)]: cols[f"{n}__{a}"] for n, a in specs if (n, a) in label}
            return out

        for n, a in specs:
            key = label[(n, a)]
            if n == "efficiency_j_th":
                continue
            out.series[key] = _combine_fleet([c[f"{n}__{a}"] for c in per.values()], mx.BY_NAME[n].fleet, len(buckets))
        if want_eff:
            power = _combine_fleet([c["power_w__avg"] for c in per.values()], "sum", len(buckets))
            rate = _combine_fleet([c["hashrate_hs__avg"] for c in per.values()], "sum", len(buckets))
            out.series["efficiency_j_th"] = [
                (p / (h / 1e12)) if p and h and h > 0 else None for p, h in zip(power, rate, strict=True)
            ]
        return out

    async def latest_ts(self, device_id: str) -> int | None:
        v = await self.db.scalar("SELECT MAX(ts) FROM samples WHERE device_id = ?", (device_id,))
        return int(v) if v is not None else None

    async def availability(self, start: float, end: float | None = None) -> dict[str, float]:
        """Fraction of polls that succeeded per device in the window (from the 1m rollup)."""
        end = end if end is not None else time.time()
        rows = await self.db.fetchall(
            "SELECT device_id, SUM(online * n) * 1.0 / NULLIF(SUM(n), 0) AS a FROM samples_1m "
            "WHERE bucket >= ? AND bucket < ? GROUP BY device_id",
            (int(start), int(end)),
        )
        return {r["device_id"]: float(r["a"]) for r in rows if r["a"] is not None}


def _combine_fleet(columns: list[list[float | None]], how: str, length: int) -> list[float | None]:
    result: list[float | None] = []
    for i in range(length):
        vals = [v for c in columns if (v := c[i]) is not None]
        if not vals:
            result.append(None)
        elif how == "sum":
            result.append(sum(vals))
        elif how == "max":
            result.append(max(vals))
        else:
            result.append(sum(vals) / len(vals))
    return result
