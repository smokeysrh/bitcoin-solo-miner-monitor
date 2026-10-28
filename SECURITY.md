# Security

## Reporting a problem

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on the repository. Don't open a public issue for something exploitable. You'll get an answer within a few days. This is a hobby-scale project, so please be patient, and I'll credit you in the CHANGELOG if you like.

Supported: the latest release.

## Who can do what

The app is meant for a home network. It is **open by default on first start** on the configured host (all interfaces by default). Set authentication before sharing access beyond a trusted home network; use HTTPS for remote access. Interactive setup offers a password. `bsmm setup --yes` skips that prompt, so arrange authentication first. `BSMM_ADMIN_PASSWORD` sets the password at startup; keep it in a protected environment rather than shell history or shared files.

| Scope | Can |
| --- | --- |
| `read` | See everything except secrets. Safe for monitoring agents. |
| `control` | Also scan, add or edit miners and run miner actions (restart, pause, pool change...), within Settings → Safety. |
| `admin` | Everything, including settings, tokens and passwords. |

- Browser sign-in uses a password and an HttpOnly, SameSite=Lax session cookie (`Secure` over HTTPS). Wrong passwords lock that address out for a growing delay.
- Scripts and agents use bearer tokens (`bsmm token create`). Only a hash of each token is stored; the token is shown once.
- Passwords are hashed with scrypt.
- Cookie-authenticated writes from another origin are rejected.

## Secrets

RPC logins, miner web passwords, bot tokens and webhook URLs are encrypted at rest (Fernet) with a key in the data directory (mode 0600), or in `BSMM_SECRET_KEY`. They are **write-only**: no API endpoint returns them, and the config export leaves them out. A database backup contains them still encrypted; the key (`secret.key`) is not in it. Anyone who can read both the database and the key file can decrypt them, so treat the data directory like a password store.

Back up the database and keep a protected copy of the key before an upgrade. On Windows, protect the folder with the account's access permissions. Enter credentials through secure app fields; keep tokens, RPC passwords and wallet addresses out of chat, logs and screenshots. Review diagnostics and captures before posting them.

## Network behaviour

- Network scans only touch private, loopback, link-local and CGNAT ranges. Public ranges are refused.
- The app talks to miners, configured node/pool sources, enabled public network-data services and GitHub release checks. Selected notification channels send alerts to their configured destinations. There is no telemetry.
- `BSMM_OFFLINE=1` disables automatic public network-data, price and release checks. Configured sources and alert destinations still make requests. `BSMM_NO_UPDATE_CHECK=1` skips release checks alone.
- Responses carry a strict Content-Security-Policy (no inline scripts, no framing), `nosniff` and `no-referrer`.
- Miner actions are audited (who, what, when, result).

## Limits you should know

- Many AxeOS and cgminer firmware builds expose unauthenticated controls. Keep miners on a trusted network and restrict dashboard access too; an authorized dashboard user can send controls through it.
- Don't put the dashboard on the public internet without a password and HTTPS in front of it (a reverse proxy, Tailscale or Cloudflare Tunnel is the usual way).
- A wrong payout address loses a found block. The app and its agent guide insist on read-back before changing one.
- Agents should begin with monitoring, show discovery results and wait for confirmation before adoption. Ask before hardware controls, pool/payout changes, tuning, firmware changes or deleting data. These are agent instructions; unattended CLI commands such as `setup --yes` can act without a further prompt.
