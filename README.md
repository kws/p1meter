# DSMR → MQTT Bridge

A small, reliable daemon that reads raw DSMR P1 telegrams from a Dutch smart meter over a serial connection and publishes them unchanged to MQTT for downstream decoding and processing.

## Features

- Reads DSMR telegrams from P1 port via USB serial
- Detects telegram boundaries (`/` … `!`)
- Publishes full telegrams to MQTT
- Publishes status (online/offline) via MQTT LWT
- Auto-reconnect on serial or MQTT disconnects
- Graceful shutdown handling
- Cross-compilation support for Raspberry Pi

## Requirements

- Go ≥ 1.21
- MQTT broker (e.g. Mosquitto)
- USB FTDI-based P1 cable
- DSMR 5.0 smart meter (e.g. Landis+Gyr E360)

## Quick Start

### Build

```bash
# Build for local platform
make build

# Cross-compile for Raspberry Pi (ARM64)
make build-pi

# Cross-compile for Raspberry Pi (ARM32)
make build-pi32
```

### Run

```bash
./bin/dsmr-mqtt \
  -serial-device /dev/ttyUSB0 \
  -mqtt-broker tcp://localhost:1883 \
  -mqtt-client-id dsmr-bridge \
  -mqtt-username myuser \
  -mqtt-password mypass
```

Or using environment variables:

```bash
export DSMR_SERIAL_DEVICE=/dev/ttyUSB0
export DSMR_MQTT_BROKER=tcp://localhost:1883
export DSMR_MQTT_CLIENT_ID=dsmr-bridge
export DSMR_MQTT_USERNAME=myuser
export DSMR_MQTT_PASSWORD=mypass

./bin/dsmr-mqtt
```

## Configuration

### Command-line Flags

- `-serial-device`: Serial device path (default: `/dev/ttyUSB0`)
- `-mqtt-broker`: MQTT broker URL (required)
- `-mqtt-client-id`: MQTT client ID (required)
- `-mqtt-username`: MQTT username (optional)
- `-mqtt-password`: MQTT password (optional)

### Environment Variables

- `DSMR_SERIAL_DEVICE`: Serial device path
- `DSMR_MQTT_BROKER`: MQTT broker URL
- `DSMR_MQTT_CLIENT_ID`: MQTT client ID
- `DSMR_MQTT_USERNAME`: MQTT username
- `DSMR_MQTT_PASSWORD`: MQTT password

Environment variables take precedence over command-line flags.

## MQTT Topics

| Topic               | Retained | Payload                   |
| ------------------- | -------- | ------------------------- |
| `dsmr/raw/telegram` | No       | Full DSMR telegram text   |
| `dsmr/raw/latest`   | Yes      | Most recent full telegram |
| `dsmr/status`       | Yes      | `online` / `offline`      |

All topics use QoS 1. The `dsmr/status` topic uses Last Will and Testament to publish `offline` if the connection is lost unexpectedly.

## Cross-Compilation

### From macOS to Raspberry Pi

The Makefile includes targets for cross-compilation:

```bash
# For Raspberry Pi 4 (ARM64)
make build-pi

# For older Raspberry Pi models (ARM32)
make build-pi32
```

The compiled binary will be in the `bin/` directory. Transfer it to your Raspberry Pi and make it executable:

```bash
scp bin/dsmr-mqtt-linux-arm64 pi@raspberrypi.local:~/dsmr-mqtt
ssh pi@raspberrypi.local "chmod +x ~/dsmr-mqtt"
```

## Systemd Service

Example systemd service file (`/etc/systemd/system/dsmr-mqtt.service`):

```ini
[Unit]
Description=DSMR to MQTT Bridge
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/home/pi/dsmr-mqtt \
  -serial-device /dev/ttyUSB0 \
  -mqtt-broker tcp://localhost:1883 \
  -mqtt-client-id dsmr-bridge \
  -mqtt-username myuser \
  -mqtt-password mypass
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dsmr-mqtt
sudo systemctl start dsmr-mqtt
```

## Serial Port Settings

The bridge uses the following serial port settings (DSMR standard):

- Baud rate: 115200
- Data bits: 8
- Parity: None
- Stop bits: 1

## Architecture

The application uses a channel-based architecture for non-blocking operation:

1. **Serial Reader**: Reads lines from the serial port with automatic retry on errors
2. **Telegram Framer**: Detects telegram boundaries (`/` start, `!` end)
3. **MQTT Publisher**: Publishes telegrams to MQTT with auto-reconnect

All components communicate via Go channels to prevent blocking.

## License

See LICENSE file for details.

