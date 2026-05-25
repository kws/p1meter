# P1 Smart Meter

Many Dutch smart meters expose a local "P1" serial port that emits DSMR
telegrams: plain-text snapshots of electricity and gas meter readings. This
project turns those telegrams into MQTT messages that can be consumed by home
automation systems, dashboards, or archivers.

The pipeline has two parts:

1. A small Go bridge reads the P1 serial port and publishes each raw DSMR
   telegram to MQTT.
2. A Python decoder subscribes to those raw telegrams, parses the useful fields,
   and republishes structured electricity and gas readings.

The two pieces live together because they share the same MQTT topics and data
contract.

## Layout

- `p1-to-mqtt/`: Go bridge that reads DSMR telegrams from the physical P1 serial
  cable and publishes the raw telegrams to MQTT.
- `p1-decoder/`: Python decoder that subscribes to the raw MQTT telegrams,
  parses them, and publishes structured electricity and gas readings.
- `p1-decoder/docker/`: Docker Compose runtime for the Python decoder services.

## Deployment Topology

A typical deployment looks like this:

1. Smart meter P1 USB cable is attached to a small always-on host.
2. The Go bridge runs as a service on that host and reads the P1 serial device.
3. The bridge publishes raw telegrams to an MQTT broker.
4. The Python `p1-stream` service runs in Docker.
5. `p1-stream` subscribes to `dsmr/raw/telegram` and publishes structured JSON
   to `dsmr/reading/electricity` and `dsmr/reading/gas`.
6. A home automation system such as OpenHAB consumes those structured topics.

The Docker Compose file also defines an archive service named `p1-decoder`. You
can run either or both Python services depending on whether raw telegram
archiving is useful for your setup.

## MQTT Topics

| Topic | Producer | Consumer | Payload |
| --- | --- | --- | --- |
| `dsmr/status` | `p1-to-mqtt` | OpenHAB | retained `online` / `offline` |
| `dsmr/raw/telegram` | `p1-to-mqtt` | `p1-decoder` | raw DSMR telegram text |
| `dsmr/reading/electricity` | `p1-stream` | OpenHAB | parsed electricity JSON |
| `dsmr/reading/gas` | `p1-stream` | OpenHAB | parsed gas JSON |

## Deployment Notes

The bridge is intended to run as a systemd service. Use an environment file for
MQTT credentials and prefer a stable `/dev/serial/by-id/...` path for the P1
cable instead of `/dev/ttyUSB0`.

The Python decoder is intended to run in Docker. GitHub Actions builds:

1. The Go bridge binary for `linux/arm64`.
2. The Python decoder Docker image.

The Docker image workflow publishes `docker.io/kws/p1-decoder` on pushes to
`main` and version tags. Configure these repository secrets before expecting a
push to Docker Hub:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## License

MIT. See `LICENSE`.
