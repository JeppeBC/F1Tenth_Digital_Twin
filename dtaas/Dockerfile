# F1Tenth digital twin, packaged for DTaaS.
#
# Build context MUST be the repo root (F1Tenth_DTaaS/), not this dtaas/ folder,
# so we can COPY the original, untouched files from ../src/. From the repo root:
#
#   docker build -f dtaas/Dockerfile -t f1tenth-dtaas:latest .
#
# Base image already provides ROS2 Humble on Ubuntu 22.04 + XFCE desktop
# exposed over noVNC on port 80 (see dtaas/compose/docker-compose.f1tenth.yml).
FROM ghcr.io/tiryoh/ros2-desktop-vnc:humble

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV F1TENTH_WS=/opt/f1tenth_ws

# ---------------------------------------------------------------------------
# f1tenth_gym (the physics engine f1tenth_gym_ros wraps) — installed as an
# editable pip package per upstream instructions.
# ---------------------------------------------------------------------------
RUN git clone --depth 1 https://github.com/f1tenth/f1tenth_gym.git /opt/f1tenth_gym \
    && pip3 install --no-cache-dir -e /opt/f1tenth_gym

# f1tenth_gym pulls in numba (JIT for base_classes.py). At import time numba
# probes for the apt-shipped python3-coverage (6.2) and, on this pairing,
# crashes with "AttributeError: module 'coverage' has no attribute 'types'"
# — coverage isn't used for anything at runtime here, so just remove it
# rather than chase exact version compatibility.
RUN apt-get remove -y --purge python3-coverage \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# f1tenth_gym_ros — the simulator + RViz2 bridge (gym_bridge_launch.py)
# ---------------------------------------------------------------------------
RUN mkdir -p ${F1TENTH_WS}/src \
    && git clone --depth 1 https://github.com/f1tenth/f1tenth_gym_ros.git \
         ${F1TENTH_WS}/src/f1tenth_gym_ros

# Upstream ships config/sim.yaml with a placeholder map_path — point it at the
# bundled Levine Hall map inside this image (known first-run gotcha).
RUN sed -i \
    "s#map_path:.*#map_path: '${F1TENTH_WS}/src/f1tenth_gym_ros/maps/levine'#" \
    ${F1TENTH_WS}/src/f1tenth_gym_ros/config/sim.yaml

# ---------------------------------------------------------------------------
# dt_pt_bridge — our own package wrapping the DT<->PT bridge/logger nodes.
# The package skeleton (setup.py, package.xml, launch file) lives under
# dtaas/ros2_ws/src/dt_pt_bridge/ in the repo; the actual node *logic* is
# copied straight from the repo's top-level src/ so there is exactly one
# copy of that code — this Dockerfile is the only place it's duplicated,
# and only inside the built image.
# ---------------------------------------------------------------------------
COPY dtaas/ros2_ws/src/dt_pt_bridge ${F1TENTH_WS}/src/dt_pt_bridge
COPY src/dt_pt_bridge.py \
     src/dt_pt_listener.py \
     src/pt_odom_receiver.py \
     src/latency_logger.py \
     src/trajectory_logger.py \
     src/ackermann_keyboard_teleop.py \
     ${F1TENTH_WS}/src/dt_pt_bridge/dt_pt_bridge/

# ---------------------------------------------------------------------------
# ROS2 dependencies + colcon build
#
# One RUN so the apt package index from `apt-get update` is still valid when
# `rosdep install` shells out to apt for f1tenth_gym_ros's own dependencies
# (e.g. ros-humble-joint-state-publisher) a few lines later — splitting this
# into two RUNs and clearing /var/lib/apt/lists/* in between (the "textbook"
# apt-cleanup pattern) starves that second apt-get with an empty index.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-ackermann-msgs \
        ros-humble-topic-tools \
        python3-transforms3d \
    && /bin/bash -c "\
        source /opt/ros/${ROS_DISTRO}/setup.bash && \
        (rosdep update || true) && \
        cd ${F1TENTH_WS} && \
        rosdep install -i --from-path src --rosdistro ${ROS_DISTRO} -y --skip-keys f1tenth_gym && \
        colcon build --symlink-install \
        " \
    && rm -rf /var/lib/apt/lists/*

# Make ROS2 + the workspace overlay available to every shell, including a
# plain `docker exec -it ... bash` (interactive, non-login — reads
# /etc/bash.bashrc directly; /home/ubuntu/.bashrc, where the base image
# sources ROS2, only applies to the desktop user's own sessions). Also
# world-readable/writable so the non-root desktop user can rebuild/edit it.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /etc/bash.bashrc \
    && echo "source ${F1TENTH_WS}/install/setup.bash" >> /etc/bash.bashrc \
    && chmod -R a+rwX ${F1TENTH_WS} /opt/f1tenth_gym

# Data + benchmark output directory shared with the host (see compose file)
RUN mkdir -p /workspace/f1tenth/data && chmod -R a+rwX /workspace/f1tenth

# ---------------------------------------------------------------------------
# Auto-launch the ROS2 stack (sim, RViz2, bridge, loggers) as a native child
# of the MATE desktop session via XDG autostart, instead of injecting it
# from outside with `docker exec`. `docker exec` spawns a process outside
# the session's process tree, and it could not get RViz2/Qt talking to the
# VNC X server no matter which DISPLAY/XAUTHORITY combination was passed —
# an autostart .desktop entry runs as a genuine child of the same xstartup
# chain that starts mate-session itself, so it inherits a working X11
# connection for free, the same way every other desktop app in this image
# does. PT_HOST comes from the container's own environment (see
# docker-compose.f1tenth.yml), so no launch arguments need passing in here.
# ---------------------------------------------------------------------------
# The "ubuntu" desktop user doesn't exist yet at image-build time — the base
# image's /entrypoint.sh creates it at CONTAINER STARTUP (`useradd`), then
# does `cp -r /root/.config $HOME && chown -R ubuntu:ubuntu $HOME`. So the
# autostart entry has to be staged under /root/.config here and let that
# existing provisioning step carry it over — writing straight to
# /home/ubuntu/.config at build time fails (no such user yet) and would be
# overwritten by that same cp anyway.
RUN mkdir -p /root/.config/autostart

COPY <<'EOF' /opt/f1tenth_ws/launch_dt.sh
#!/bin/bash
# Disposable local dev container behind no auth of its own but the DTaaS
# stack's — the idle screensaver lock is just friction here, not a useful
# boundary. Runs as this same autostart entry so it fires every session.
gsettings set org.mate.screensaver idle-activation-enabled false 2>/dev/null || true
gsettings set org.mate.screensaver lock-enabled false 2>/dev/null || true

source /opt/ros/humble/setup.bash
source /opt/f1tenth_ws/install/setup.bash
mkdir -p /workspace/f1tenth/data
exec ros2 launch dt_pt_bridge f1tenth_dt.launch.py \
    pt_host:="${PT_HOST:-172.20.10.8}" \
    > /workspace/f1tenth/data/launch_dt.log 2>&1
EOF

COPY <<'EOF' /root/.config/autostart/f1tenth-dt.desktop
[Desktop Entry]
Type=Application
Name=F1Tenth DT
Exec=/opt/f1tenth_ws/launch_dt.sh
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

RUN chmod +x /opt/f1tenth_ws/launch_dt.sh

WORKDIR ${F1TENTH_WS}
