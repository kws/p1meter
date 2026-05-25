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

## Deployment Topology

The intended deployment shape is:

1. Smart meter P1 USB cable is attached to a small always-on host.
2. The Go bridge runs as a service on that host and reads the P1 serial device.
3. The bridge publishes raw telegrams to an MQTT broker.
4. The Python `p1-stream` service runs in Docker.
5. `p1-stream` subscribes to `dsmr/raw/telegram` and publishes structured JSON
   to `dsmr/reading/electricity` and `dsmr/reading/gas`.
6. A home automation system such as OpenHAB consumes those structured topics.

The compose file also defines an archive service named `p1-decoder`. The live
deployment can run either or both services depending on whether raw telegram
archiving is wanted.

## MQTT Topics

| Topic | Producer | Consumer | Payload |
| --- | --- | --- | --- |
| `dsmr/status` | `p1-to-mqtt` | OpenHAB | retained `online` / `offline` |
| `dsmr/raw/telegram` | `p1-to-mqtt` | `p1-decoder` | raw DSMR telegram text |
| `dsmr/reading/electricity` | `p1-stream` | OpenHAB | parsed electricity JSON |
| `dsmr/reading/gas` | `p1-stream` | OpenHAB | parsed gas JSON |

## Deployment Direction

The bridge should run as a systemd service managed by infrastructure
configuration. The service should use an environment file for MQTT credentials
and a stable `/dev/serial/by-id/...` path for the P1 cable.

The Python decoder should be built as a Docker image and deployed from that
image rather than relying on a checked-out source tree on the Docker host. The
next step is to add GitHub Actions for:

1. Building the Go bridge binary for `linux/arm64`.
2. Building and pushing the Python decoder image to Docker Hub.
