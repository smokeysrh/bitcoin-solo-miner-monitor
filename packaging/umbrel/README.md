# Umbrel app template

An app definition (`umbrel-app.yml` + `docker-compose.yml`) for the [Umbrel community app store](https://github.com/getumbrel/umbrel-community-app-store) format.

**Status: template, not yet run on a real Umbrel.** What is verified: the Docker image it points to builds, starts, reports healthy, runs as a non-root user and keeps its data in `/data`. What is not: Umbrel's app proxy, the `${APP_DATA_DIR}` path and the store submission rules.

To try it, copy this folder into a community app store repository as `bitcoin-solo-miner-monitor/` (with a `umbrel-app-store.yml` next to it) and install from the Umbrel app store UI.

Notes:

- `BSMM_AUTH=none` relies on Umbrel's own login in front of the app. Do not publish the app's port outside Umbrel.
- Inside Umbrel the container cannot scan your home network. Add miners by address or enter your range in the scan box.
- Pointing the app at the Umbrel Bitcoin node: use the node's RPC details from Umbrel's *Bitcoin Node → Connect* page, in Settings → Node & pool.
