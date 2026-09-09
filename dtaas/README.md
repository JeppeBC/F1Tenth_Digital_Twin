# F1Tenth DT — DTaaS integration

This folder packages the F1Tenth digital twin (the rest of this repo:
`src/`, `benchmarks/`, top-level `README.md`) to run inside DTaaS, without
changing anything outside `dtaas/`. Nothing in `src/` is modified — the
Docker image build copies those files in as-is; the originals stay exactly
as they were for your existing WSL2 workflow.

## What's here

```
dtaas/
  Dockerfile                    ROS2 Humble + f1tenth_gym(_ros) + dt_pt_bridge,
                                 built FROM ghcr.io/tiryoh/ros2-desktop-vnc:humble
  ros2_ws/src/dt_pt_bridge/     New ROS2 package: entry points + launch file for
                                 the nodes in ../../src/ (copied in at build time)
  digital_twins/f1tenth/        DTaaS lifecycle scripts (create/execute/.../clean)
  compose/                      docker-compose.f1tenth.yml (overlay) + Grafana
                                 provisioning (InfluxDB datasource, dashboard)
  scripts/csv_to_influx.py      Pushes a run's CSVs into InfluxDB (used by `save`)
  data/                         Per-run CSV output, bind-mounted from the container
                                 (created empty by lifecycle/execute on first run)
```

## Architecture note: this runs *alongside* DTaaS, not *inside* it

`f1tenth-dt`/`influxdb`/`grafana` are defined in `compose/docker-compose.f1tenth.yml`, a separate
compose file from `workspace-dex-localhost/docker-compose.yml` — not a new service bolted onto
that file. That was deliberate: RViz2 needs a full desktop GUI environment DTaaS's `user`
workspace container doesn't have, so this ships as its own container instead. Practically, that
means:

- It is **not** visible or launchable from DTaaS's web client (`localhost/`) — it bypasses
  Traefik and sits on its own fixed ports (6080/3000/8086).
- The two stacks are independent as far as Docker Compose is concerned. A plain
  `docker compose down` from `workspace-dex-localhost/` only knows about *that* folder's
  `docker-compose.yml` — it will **not** stop `f1tenth-dt`/`influxdb`/`grafana`, leaving them
  running on their ports. Use `lifecycle/down-all` (or `down-all.ps1`) to stop both together.
- They do share one thing: when both are up, their containers land on the same Docker network
  (`workspace-dex-localhost_default`), which is why bringing only one down can leave the other
  holding that network open ("resource is still in use" — harmless, not an error).

## Shell: Bash vs PowerShell

The `lifecycle/*` scripts are Bash scripts (no `.sh` extension, `#!/usr/bin/env bash`) — running
`./execute` only works in a Bash-compatible shell (Git Bash, WSL). In PowerShell, either:

- Open Git Bash instead for these commands, or
- Prefix with `bash`: `bash ./execute` (PowerShell can't interpret the shebang line itself, and
  double-clicking / `./execute` there just opens it as a text file in your browser).

`down-all.ps1` (at the `dtaas/` root) is the one script here written for PowerShell directly —
run it with `powershell -File dtaas\down-all.ps1`.

## Prerequisites

1. `workspace-dex-localhost` already running (see the main DTaaS setup —
   `docker compose ps` from that folder should show 5 healthy containers).
2. Copy the config template and set your machine's paths:
   ```
   cp digital_twins/f1tenth/config/dt.env.example digital_twins/f1tenth/config/dt.env
   ```
   Edit `dt.env`: `DTAAS_DIR` must point at your `workspace-dex-localhost/workspace-dex-localhost`
   folder; `PT_HOST` is the car's IP on your WiFi/hotspot. Both `down-all` and `down-all.ps1` read
   the same file, so there's one source of truth regardless of which shell you use.
3. (For `lifecycle/analyze`, which runs on the host, not in the container)
   `pip install -r ../requirements.txt` once, in whatever Python env you use on Windows/WSL2.

## Running it

```bash
cd digital_twins/f1tenth/lifecycle
./create      # builds the image (first run: long — clones + colcon builds ROS2 pkgs)
./execute     # starts f1tenth-dt + influxdb + grafana, launches sim+RViz2+bridge
```

Then, unchanged, on the car:
```bash
cd Desktop/F1Tenth_DTaaS/ && export ROS_DOMAIN_ID=0
python3 dt_pt_listener.py --port 9870 --echo-back --send-odom --dt-host <this-machine-ip> --odom-port 9871
```

- **RViz2 desktop:** http://localhost:6080/ (noVNC — open a terminal there for keyboard teleop:
  `ros2 run dt_pt_bridge ackermann_keyboard_teleop`)
- **Grafana:** http://localhost:3000/ (admin / admin, change on first login) — F1Tenth folder has
  a starter "DT vs PT" dashboard (latency + X/Y position). It's provisioned but I haven't been
  able to visually verify the panels render correctly — check it after your first `save` and
  adjust in the Grafana UI if a query needs tweaking.
- **InfluxDB:** http://localhost:8086/

```bash
./terminate   # stops the sim (influxdb/grafana keep running, data intact)
./save        # pushes the latest run's CSVs into InfluxDB for Grafana
./analyze     # runs the ORIGINAL plot_latency.py / plot_trajectory.py on the latest run
./down-all    # stops f1tenth-dt + influxdb + grafana AND the base DTaaS stack together
./clean       # full reset — wipes InfluxDB/Grafana data (NOT dtaas/data/ CSVs)
```

All lifecycle scripts default to the most recently created run under `data/`,
or take an explicit run directory as `$1`.

## Known caveats / things to check on first run

Confirmed working end-to-end as of the last test: `create` builds cleanly on ROS2 Humble
(despite `f1tenth_gym_ros` being documented as tested on Foxy), RViz2 renders fine via software
rendering with no extra flags needed, and `ros2 topic list` shows the full expected set
(`/scan`, `/map`, `/odom`, `/ego_racecar/odom`, `/drive`, `/clock`, etc.). Two build-time bugs
that are already fixed in this Dockerfile but worth knowing about if you're editing it further:
`docker compose build` (not plain `docker build`) fails on the `&` in this repo's `R&D` parent
folder — `create` uses plain `docker build` for that reason — and `f1tenth_gym`'s `numba`
dependency crashes against the apt-shipped `python3-coverage`, which the Dockerfile removes.

- **UDP ports 9871/9872** are published from the container so the car can reach
  `pt_odom_receiver` unsolicited. If odom never arrives, check Windows Firewall isn't blocking
  inbound UDP on those ports for Docker Desktop's network.
- **Grafana dashboard** — provisioned from `compose/grafana/dashboards/f1tenth_dt.json` and
  confirmed to load (datasource + dashboard both show up via Grafana's API), but written against
  the Influx schema `csv_to_influx.py` produces without ever feeding it a real session's data —
  treat panel layout/queries as a starting point until you've run `save` with actual car data and
  checked it renders sensibly.

## Where the bicycle model fits

See `digital_twins/f1tenth/lifecycle/evolve` — the planned improved bicycle model plugs in as a
new node/patch under `ros2_ws/src/dt_pt_bridge/`, wired into
`ros2_ws/src/dt_pt_bridge/launch/f1tenth_dt.launch.py`, and evaluated with the same
`analyze`/`trajectory_logger.py` pipeline already in place.
