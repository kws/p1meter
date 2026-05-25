# P1 Decoder

Python services for the P1 smart meter pipeline. The decoder subscribes to raw
DSMR telegrams from MQTT, parses them, and publishes structured JSON readings
for OpenHAB.

This package lives inside the P1 smart meter monorepo. The paired serial bridge
is in `../p1-to-mqtt`.

## Services

- `python -m p1_decoder.stream`: subscribes to `dsmr/raw/telegram` and publishes
  parsed readings to `dsmr/reading/electricity` and `dsmr/reading/gas`.
- `python -m p1_decoder.archive`: subscribes to raw telegrams and writes archive
  files under `/app/archive`.

The stream and archive services can be run independently. Most home automation
setups only need `p1-stream`; `p1-decoder` is useful when you also want a raw
telegram archive.

## Configuration

Configuration is read from environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MQTT_TOPIC` | `dsmr/raw/telegram` | Raw telegram subscription topic |
| `MQTT_USERNAME` | unset | Optional MQTT username |
| `MQTT_PASSWORD` | unset | Optional MQTT password |

For Docker Compose, put these values in `docker/.env`.

## Docker

```bash
cd docker
docker compose up --build p1-stream
```

The next deployment step is to build this service as a published Docker image so
the runtime host does not need a checked-out source tree.
