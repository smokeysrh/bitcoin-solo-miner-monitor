# Security

## Reporting a problem

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on the repository. Don't open a public issue for something exploitable. You'll get an answer within a few days. This is a hobby-scale project, so please be patient, and I'll credit you in the CHANGELOG if you like.

Supported: the latest release.

## Who can do what

The app is meant for a home network. It is **open by default on first start** so setup is painless, and the wizard (and `bsmm setup`) offers to set a password. If the app is reachable by anyone you don't trust, set one. `BSMM_ADMIN_PASSWORD` enforces it from the first request.

| Scope | Can |
| --- | --- |
| `read` | See everything except secrets. Safe for monitoring agents. |
| `control` | Also run miner actions (restart, pause, pool change...), and only inside the limits of Settings → Safety. |
| `admin` | Everything, including settings, tokens and passwords. |

- Browser sign-in uses a password and an HttpOnly, SameSite=Lax session cookie (`Secure` over HTTPS). Wrong passwords lock that address out for a growing delay.
- Scripts and agents use bearer tokens (`bsmm token create`). Only a hash of each token is stored; the token is shown once.
- Passwords are hashed with scrypt.
- Cookie-authenticated writes from another origin are rejected.

## Secrets

RPC logins, miner web passwords, bot tokens and webhook URLs are encrypted at rest (Fernet) with a key in the data directory (mode 0600), or in `BSMM_SECRET_KEY`. They are **write-only**: no API endpoint returns them, and the config export leaves them out. A database backup contains them still encrypted; the key (`secret.key`) is not in it. Anyone who can read both the database and the key file can decrypt them, so treat the data directory like a password store.

## Network behaviour

- Network scans only touch private, loopback, link-local and CGNAT ranges. Public ranges are refused.
- The app talks to your miners, your node/pool and (unless `BSMM_OFFLINE=1`) mempool.space and GitHub for update checks. There is no telemetry.
- Responses carry a strict Content-Security-Policy (no inline scripts, no framing), `nosniff` and `no-referrer`.
- Miner actions are audited (who, what, when, result).

## Limits you should know

- Miners themselves (AxeOS, cgminer) have no authentication on most firmware. Anyone on your LAN can already control them. This app doesn't make that worse, but it doesn't fix it either.
- Don't put the dashboard on the public internet without a password and HTTPS in front of it (a reverse proxy, Tailscale or Cloudflare Tunnel is the usual way).
- A wrong payout address loses a found block. The app and its agent guide insist on read-back before changing one.
