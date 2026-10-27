"""The numeric telemetry fields we keep as time series, and how each one is rolled up.

One registry drives the table definitions, the rollup SQL and the history API, so adding a metric
is a one-line change here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    #: gauge = a level (avg/min/max), counter = only ever grows (keep the max), flag = 0/1 (avg = availability)
    kind: str
    #: how to combine devices into a fleet series: sum | mean | max
    fleet: str
    keep_min: bool = False
    keep_max: bool = False
    unit: str = ""
    label: str = ""


METRICS: tuple[Metric, ...] = (
    Metric("online", "flag", "sum", unit="devices", label="Devices online"),
    Metric("hashrate_hs", "gauge", "sum", True, True, "H/s", "Hashrate"),
    Metric("power_w", "gauge", "sum", False, True, "W", "Power"),
    Metric("efficiency_j_th", "gauge", "mean", False, False, "J/TH", "Efficiency"),
    Metric("temp_asic_c", "gauge", "max", False, True, "°C", "ASIC temperature"),
    Metric("temp_vr_c", "gauge", "max", False, True, "°C", "Voltage regulator temperature"),
    Metric("temp_board_c", "gauge", "mean", False, False, "°C", "Board temperature"),
    Metric("fan_pct", "gauge", "mean", False, False, "%", "Fan speed"),
    Metric("fan_rpm", "gauge", "mean", False, False, "rpm", "Fan speed (rpm)"),
    Metric("voltage_in_v", "gauge", "mean", False, False, "V", "Input voltage"),
    Metric("current_a", "gauge", "sum", False, False, "A", "Input current"),
    Metric("frequency_mhz", "gauge", "mean", False, False, "MHz", "ASIC frequency"),
    Metric("core_voltage_mv", "gauge", "mean", False, False, "mV", "Core voltage"),
    Metric("hw_error_pct", "gauge", "mean", False, False, "%", "Hardware error rate"),
    Metric("reject_rate_pct", "gauge", "mean", False, False, "%", "Share reject rate"),
    Metric("wifi_rssi_dbm", "gauge", "mean", False, False, "dBm", "WiFi signal"),
    Metric("pool_ping_ms", "gauge", "mean", False, False, "ms", "Pool latency"),
    Metric("free_heap_bytes", "gauge", "mean", False, False, "B", "Free memory"),
    Metric("shares_accepted", "counter", "sum", unit="shares", label="Accepted shares"),
    Metric("shares_rejected", "counter", "sum", unit="shares", label="Rejected shares"),
    Metric("best_diff", "counter", "max", unit="", label="Best share difficulty"),
    Metric("uptime_s", "counter", "max", unit="s", label="Uptime"),
)

BY_NAME: dict[str, Metric] = {m.name: m for m in METRICS}
NAMES: tuple[str, ...] = tuple(m.name for m in METRICS)

#: rollup levels: (table, bucket seconds, source table)
LEVELS: tuple[tuple[str, int, str], ...] = (
    ("samples_1m", 60, "samples"),
    ("samples_1h", 3600, "samples_1m"),
    ("samples_1d", 86400, "samples_1h"),
)


def rollup_columns(m: Metric) -> list[str]:
    cols = [m.name]
    if m.keep_min:
        cols.append(f"{m.name}_min")
    if m.keep_max:
        cols.append(f"{m.name}_max")
    return cols


def raw_table_ddl() -> str:
    cols = ",\n  ".join(f"{m.name} REAL" for m in METRICS)
    return f"""CREATE TABLE samples (
  device_id TEXT NOT NULL,
  ts INTEGER NOT NULL,
  {cols},
  PRIMARY KEY (device_id, ts)
) WITHOUT ROWID;"""


def rollup_table_ddl(table: str) -> str:
    cols: list[str] = []
    for m in METRICS:
        cols.extend(f"{c} REAL" for c in rollup_columns(m))
    body = ",\n  ".join(cols)
    return f"""CREATE TABLE {table} (
  device_id TEXT NOT NULL,
  bucket INTEGER NOT NULL,
  n INTEGER NOT NULL,
  {body},
  PRIMARY KEY (device_id, bucket)
) WITHOUT ROWID;"""


def rollup_sql(target: str, bucket_s: int, source: str) -> str:
    """INSERT..SELECT that (re)computes buckets in [:t0, :t1) from the finer table. Idempotent."""
    from_raw = source == "samples"
    ts_col = "ts" if from_raw else "bucket"
    insert_cols = ["device_id", "bucket", "n"]
    select_exprs = ["device_id", f"({ts_col} / {bucket_s}) * {bucket_s}", "COUNT(*)" if from_raw else "SUM(n)"]
    for m in METRICS:
        # raw rows: avg(x); rollup rows: weighted by n and ignoring NULLs
        def avg(col: str) -> str:
            if from_raw:
                return f"AVG({col})"
            return f"SUM(CASE WHEN {col} IS NOT NULL THEN {col} * n END) / NULLIF(SUM(CASE WHEN {col} IS NOT NULL THEN n END), 0)"

        insert_cols.append(m.name)
        if m.kind == "counter":
            select_exprs.append(f"MAX({m.name})")
        else:
            select_exprs.append(avg(m.name))
        if m.keep_min:
            insert_cols.append(f"{m.name}_min")
            select_exprs.append(f"MIN({m.name})" if from_raw else f"MIN({m.name}_min)")
        if m.keep_max:
            insert_cols.append(f"{m.name}_max")
            select_exprs.append(f"MAX({m.name})" if from_raw else f"MAX({m.name}_max)")
    updates = ", ".join(f"{c}=excluded.{c}" for c in insert_cols if c not in ("device_id", "bucket"))
    return (
        f"INSERT INTO {target} ({', '.join(insert_cols)})\n"
        f"SELECT {', '.join(select_exprs)}\nFROM {source}\n"
        f"WHERE {ts_col} >= :t0 AND {ts_col} < :t1\n"
        f"GROUP BY device_id, ({ts_col} / {bucket_s}) * {bucket_s}\n"
        f"ON CONFLICT(device_id, bucket) DO UPDATE SET {updates}"
    )
