"""A fake cgminer-API device (TCP 4028) for tests and development.

Profiles reproduce the *shape* of real replies: Canaan Avalon Nano 3 (bracketed ``MM ID0`` strings)
and a Bitmain-style Antminer (``stats`` with temp/fan fields). They are built from the documented
formats and published community captures; they are not recordings of one specific unit.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any


class CgminerSim:
    def __init__(self, profile: str = "avalon_nano3", *, seed: int | None = None) -> None:
        if profile not in ("avalon_nano3", "antminer_s19", "braiins"):
            raise ValueError(f"unknown profile {profile!r}")
        self.profile = profile
        self.rng = random.Random(seed)
        self.started = time.time()
        self.accepted = 0
        self.rejected = 0
        self.server: asyncio.base_events.Server | None = None
        self.commands: list[str] = []

    def prime(self, uptime_s: float) -> None:
        """Pretend the device has already been mining for ``uptime_s`` so counters are not empty on first view."""
        self.started = time.time() - uptime_s
        self.accepted += int(uptime_s / 25)
        self.rejected += int(self.accepted * 0.005)

    @property
    def port(self) -> int:
        assert self.server is not None
        return int(self.server.sockets[0].getsockname()[1])

    def _status(self, msg: str, code: int = 11) -> list[dict[str, Any]]:
        return [{"STATUS": "S", "When": int(time.time()), "Code": code, "Msg": msg, "Description": "cgminer 4.11.1"}]

    def _elapsed(self) -> int:
        return int(time.time() - self.started)

    def _tick(self) -> None:
        self.accepted += self.rng.randrange(0, 4)
        if self.rng.random() < 0.05:
            self.rejected += 1

    def reply(self, command: str) -> dict[str, Any]:
        self.commands.append(command)
        self._tick()
        if command == "version":
            if self.profile == "avalon_nano3":
                v = {"CGMiner": "4.11.1", "API": "3.7", "PROD": "Avalonnano", "MODEL": "nano3", "HWTYPE": "N_MM1v1_X1",
                     "SWTYPE": "MM319", "LVERSION": "25021401_4ec6bb0", "BVERSION": "25021401_4ec6bb0", "CGVERSION": "4.11.1",
                     "DNA": "0123456789abcdef"}
            elif self.profile == "braiins":
                v = {"BOSminer": "bosminer-plus-am1-s9", "API": "3.7", "Type": "Antminer S9"}
            else:
                v = {"BMMiner": "2.0.0", "API": "3.1", "Miner": "uart_trans.1.3.0.12", "CompileTime": "Fri Jan 1 00:00:00 CST 2021",
                     "Type": "Antminer S19j Pro"}
            return {"STATUS": self._status("CGMiner versions", 22), "VERSION": [v], "id": 1}
        if command == "summary":
            ghs = 3900.0 + self.rng.uniform(-60, 60) if self.profile == "avalon_nano3" else 104_000.0 + self.rng.uniform(-900, 900)
            s = {
                "Elapsed": self._elapsed(), "MHS av": ghs * 1000 * 0.99, "MHS 5s": ghs * 1000, "MHS 1m": ghs * 1000 * 0.998,
                "MHS 5m": ghs * 1000, "MHS 15m": ghs * 1000, "Found Blocks": 0, "Getworks": 120, "Accepted": self.accepted,
                "Rejected": self.rejected, "Hardware Errors": 3, "Utility": 1.2, "Discarded": 10, "Stale": 0,
                "Get Failures": 0, "Local Work": 3000, "Remote Failures": 0, "Network Blocks": 20, "Total MH": 1.0e12,
                "Work Utility": 1000.0, "Difficulty Accepted": self.accepted * 1000.0, "Difficulty Rejected": self.rejected * 1000.0,
                "Difficulty Stale": 0.0, "Best Share": 2_345_678_901, "Device Hardware%": 0.0021,
                "Device Rejected%": 0.4, "Pool Rejected%": 0.4, "Pool Stale%": 0.0, "Last getwork": int(time.time()),
            }
            return {"STATUS": self._status("Summary"), "SUMMARY": [s], "id": 1}
        if command == "pools":
            pools = [
                {"POOL": 1, "URL": "stratum+tcp://192.168.1.10:2018", "Status": "Alive", "Priority": 0, "Quota": 1, "Long Poll": "N",
                 "Getworks": 100, "Accepted": self.accepted, "Rejected": self.rejected, "Works": 1000, "Discarded": 0, "Stale": 0,
                 "Get Failures": 0, "Remote Failures": 0, "User": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq.nano1", "Last Share Time": int(time.time()),
                 "Diff1 Shares": 1000, "Proxy Type": "", "Proxy": "", "Difficulty Accepted": 1000.0, "Difficulty Rejected": 0.0,
                 "Difficulty Stale": 0.0, "Last Share Difficulty": 1000.0, "Has Stratum": True, "Stratum Active": True,
                 "Stratum URL": "192.168.1.10", "Has GBT": False, "Best Share": 1234.0, "Pool Rejected%": 0.0, "Pool Stale%": 0.0},
                {"POOL": 2, "URL": "stratum+tcp://solo.ckpool.org:3333", "Status": "Alive", "Priority": 1, "Quota": 1,
                 "Accepted": 0, "Rejected": 0, "User": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq.nano1", "Has Stratum": True, "Stratum Active": False},
            ]
            return {"STATUS": self._status("2 Pool(s)", 7), "POOLS": pools, "id": 1}
        if command == "estats" and self.profile == "avalon_nano3":
            mm = (
                "Ver[Nano3-25021401_4ec6bb0] DNA[0123456789abcdef] Elapsed[%d] MW[2000 2000 2000 2000] LW[8000] MH[0 0 0 0] HW[3] "
                "DH[0.002%%] Temp[38] TMax[87] TAvg[85] Fan1[2430] FanR[32%%] Vi[1200 1200] Vo[1210] PS[0 1193 1275 0 0 3606] "
                "GHSspd[3900.0] DHspd[0.0%%] GHSmm[3900.0] WU[3899] Freq[500.00] PG[15] Led[0] MGHS[3900.00] MTmax[87] MTavg[85] "
                "TA[4] ECHU[0 0 0 0] ECMM[0] SoftOFF[0] WORKMODE[1] WORKLEVEL[1] MPO[160]" % self._elapsed()
            )
            return {"STATUS": self._status("CGMiner stats", 70), "STATS": [{"STATS": 0, "ID": "AVA30", "Elapsed": self._elapsed(), "MM ID0": mm}], "id": 1}
        if command == "stats" and self.profile != "avalon_nano3":
            body = {"STATS": 1, "ID": "BC10", "Elapsed": self._elapsed(), "GHS 5s": "104000.5", "GHS av": 103500.2, "fan1": 5640,
                    "fan2": 5760, "fan3": 0, "fan4": 0, "temp1": 55, "temp2": 56, "temp3": 57, "temp2_1": 78, "temp2_2": 79,
                    "frequency": 525, "total_rateideal": 104000.0}
            head = {"BMMiner": "2.0.0", "Miner": "uart_trans.1.3.0.12", "Type": "Antminer S19j Pro"}
            return {"STATUS": self._status("BMMiner stats", 70), "STATS": [head, body], "id": 1}
        return {"STATUS": [{"STATUS": "E", "When": int(time.time()), "Code": 14, "Msg": "Invalid command", "Description": "cgminer"}], "id": 1}

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(4096), 3)
            try:
                command = json.loads(raw.decode()).get("command", "")
            except ValueError:
                command = raw.decode().strip()
            writer.write(json.dumps(self.reply(command)).encode() + b"\x00")
            await writer.drain()
        except (TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> CgminerSim:
        self.server = await asyncio.start_server(self._handle, host, port)
        return self

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
