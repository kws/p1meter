# P1 Smart Meter

This repository is the source of truth for the home DSMR/P1 smart meter
pipeline. It is a monorepo because the serial bridge, MQTT topics, Python
decoder, Docker runtime, and OpenHAB integration are tightly coupled.

## Layout

- `p1-to-mqtt/`: Go bridge that reads DSMR telegrams from the physical P1 serial
  cable and publishes the raw telegrams to MQTT.
- `p1-decoder/`: Python decoder that subscribes to the raw MQTT telegrams,
  parses them, and publishes structured electricity and gas readings.
- `p1-decoder/docker/`: Docker Compose runtime for the Python decoder services.

The `p1-to-mqtt` and `p1-decoder` histories were imported with `git subtree` so
the old project history is still available inside this repository.

## Live Topology

As of 2026-05-25, the working deployment is:

1. Smart meter P1 USB cable is attached to `edge-host`.
2. `edge-host` runs `dsmr-mqtt-linux-arm64` from `/opt/p1`, currently in a
   user `tmux` session.
3. The Go bridge reads `/dev/ttyUSB0`; the stable device path is
   `/dev/serial/by-id/usb-FTDI_P1_CABLE-if00-port0`.
4. The bridge publishes raw telegrams to Mosquitto on `mqtt-broker:1883`.
5. `docker-host` runs the `p1-stream` Docker container from the Python decoder
   compose stack.
6. `p1-stream` subscribes to `dsmr/raw/telegram` and publishes structured JSON
   to `dsmr/reading/electricity` and `dsmr/reading/gas`.
7. OpenHAB on `mqtt-broker` consumes those structured topics from
   `/etc/openhab/things/p1.things`.

The compose file also defines an archive service named `p1-decoder`. The live
scan on 2026-05-25 found `p1-stream` running and the archive service stopped, so
the current OpenHAB status depends on `p1-stream`.

## MQTT Topics

| Topic | Producer | Consumer | Payload |
| --- | --- | --- | --- |
| `dsmr/status` | `p1-to-mqtt` | OpenHAB | retained `online` / `offline` |
| `dsmr/raw/telegram` | `p1-to-mqtt` | `p1-decoder` | raw DSMR telegram text |
| `dsmr/reading/electricity` | `p1-stream` | OpenHAB | parsed electricity JSON |
| `dsmr/reading/gas` | `p1-stream` | OpenHAB | parsed gas JSON |

## Deployment Direction

The current bridge process on `edge-host` should move from `tmux` into a
systemd service managed by infrastructure configuration. The service should use
an environment file for MQTT credentials and the stable `/dev/serial/by-id/...`
path for the P1 cable.

The Python decoder should be built as a Docker image and deployed from that
image rather than relying on a checked-out source tree on the Docker host. The
next step is to add GitHub Actions for:

1. Building the Go bridge binary for `linux/arm64`.
2. Building and pushing the Python decoder image to Docker Hub.
