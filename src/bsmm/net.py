"""Networking helpers: HTTP client, address parsing, local-network detection, TCP probing."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import re
from collections.abc import Iterator
from urllib.parse import urlsplit

import httpx

from bsmm import __version__

USER_AGENT = f"bitcoin-solo-miner-monitor/{__version__}"
DEFAULT_TIMEOUT = httpx.Timeout(connect=3.0, read=6.0, write=6.0, pool=3.0)

#: Never scan more than this many addresses in one go unless the caller opts in explicitly.
MAX_SCAN_HOSTS = 4096


def make_http_client(timeout: httpx.Timeout | float | None = None, *, verify: bool | str = True) -> httpx.AsyncClient:
    """Shared async HTTP client.

    ESP32 miners have a handful of sockets, so keep-alive is off: one short request per poll is the
    gentlest thing we can do to them. ``verify=False`` is only ever used for self-signed local nodes
    when the user explicitly asks for it.
    """
    return httpx.AsyncClient(
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Connection": "close", "Accept": "application/json, */*;q=0.5"},
        limits=httpx.Limits(max_connections=256, max_keepalive_connections=0),
        follow_redirects=False,
        verify=verify,
    )


_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-\.]{0,251}[A-Za-z0-9])?$")


def split_host_port(text: str, default_port: int | None = None) -> tuple[str, int | None]:
    """Parse ``192.168.1.9``, ``http://192.168.1.9:8080/path``, ``miner.local:80`` or ``[fe80::1]:80``.

    Raises ``ValueError`` for anything that is not a plausible host.
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty host")
    if "://" not in raw:
        raw = "//" + raw
    parts = urlsplit(raw)
    host = parts.hostname
    if not host:
        raise ValueError(f"cannot find a host in {text!r}")
    try:
        port = parts.port
    except ValueError as e:
        raise ValueError(f"bad port in {text!r}") from e
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is None and not _HOST_RE.match(host):
        raise ValueError(f"{host!r} is not a valid host name")
    return host, (port if port is not None else default_port)


def is_private_host(host: str) -> bool:
    """True for RFC1918 / loopback / link-local / CGNAT addresses (what a home LAN uses)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host.endswith((".local", ".lan", ".home", ".internal")) or "." not in host
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip in ipaddress.ip_network("100.64.0.0/10"))


def local_ipv4_networks(include_docker: bool = False) -> list[ipaddress.IPv4Network]:
    """Subnets this machine is attached to, most useful first (private LANs, /24 at most)."""
    import ifaddr

    found: list[tuple[int, ipaddress.IPv4Network]] = []
    for adapter in ifaddr.get_adapters():
        name = (adapter.nice_name or adapter.name or "").lower()
        is_virtual = any(t in name for t in ("docker", "veth", "br-", "virbr", "vmnet", "vethernet", "wsl", "tun", "tap", "utun"))
        if is_virtual and not include_docker:
            continue
        for ip in adapter.ips:
            if not ip.is_IPv4 or not isinstance(ip.ip, str):
                continue
            try:
                addr = ipaddress.ip_address(ip.ip)
                if addr.is_loopback or addr.is_link_local or not is_private_host(ip.ip):
                    continue
                net = ipaddress.ip_network(f"{ip.ip}/{ip.network_prefix}", strict=False)
            except ValueError:
                continue
            if not isinstance(net, ipaddress.IPv4Network):
                continue
            if net.prefixlen < 24:  # a /16 sweep is rude; suggest the /24 we actually sit in
                net = ipaddress.ip_network(f"{ip.ip}/24", strict=False)
            weight = 0 if str(addr).startswith(("192.168.", "10.")) else 1
            found.append((weight, net))  # type: ignore[arg-type]
    seen: set[str] = set()
    result: list[ipaddress.IPv4Network] = []
    for _, net in sorted(found, key=lambda t: (t[0], str(t[1]))):
        if str(net) not in seen:
            seen.add(str(net))
            result.append(net)
    return result


def local_address_towards(host: str) -> str | None:
    """The address of this computer that the network would use to reach ``host`` (nothing is sent)."""
    import socket
    try:
        ip = socket.gethostbyname(host)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((ip, 9))
            addr = str(s.getsockname()[0])
    except OSError:
        return None
    return addr if addr and addr != "0.0.0.0" else None
def own_ipv4_addresses() -> set[str]:
    import ifaddr

    out: set[str] = set()
    for adapter in ifaddr.get_adapters():
        for ip in adapter.ips:
            if ip.is_IPv4 and isinstance(ip.ip, str):
                out.add(ip.ip)
    return out


def iter_hosts(cidr: str, limit: int = MAX_SCAN_HOSTS) -> Iterator[str]:
    """Usable host addresses of ``cidr`` (a single IP counts as a /32). Raises on oversize ranges."""
    try:
        net = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError as e:
        raise ValueError(f"{cidr!r} is not a valid network (example: 192.168.1.0/24)") from e
    if net.version != 4:
        raise ValueError("only IPv4 ranges can be scanned")
    count = net.num_addresses if net.prefixlen >= 31 else net.num_addresses - 2
    if count > limit:
        raise ValueError(
            f"{cidr} has {count} addresses; scanning more than {limit} at once is not allowed (use a smaller range)"
        )
    if net.prefixlen >= 31:
        yield from (str(a) for a in net)
    else:
        yield from (str(h) for h in net.hosts())


async def tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """True if a TCP connection to host:port succeeds within ``timeout`` seconds."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, TimeoutError):
        return False
    writer.close()
    with contextlib.suppress(OSError):
        await writer.wait_closed()
    return True


def redact_url(url: str) -> str:
    """Strip credentials / query secrets from a URL before it goes into a log line."""
    try:
        p = urlsplit(url)
    except ValueError:
        return "<invalid url>"
    host = p.hostname or ""
    if p.port:
        host = f"{host}:{p.port}"
    return f"{p.scheme}://{host}{p.path}" if p.scheme else host
