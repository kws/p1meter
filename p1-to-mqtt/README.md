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
- `-mqtt-client-id`: MQTT client ID (required, max 23 characters per MQTT spec)
- `-mqtt-username`: MQTT username (optional)
- `-mqtt-password`: MQTT password (optional)
- `-mqtt-tls`: Enable TLS encryption for MQTT connection (optional)
- `-verbose`: Enable verbose logging (optional)

### Environment Variables

- `DSMR_SERIAL_DEVICE`: Serial device path
- `DSMR_MQTT_BROKER`: MQTT broker URL (supports `tcp://`, `ssl://`, `tls://`, `ws://`, `wss://`)
- `DSMR_MQTT_CLIENT_ID`: MQTT client ID (max 23 characters)
- `DSMR_MQTT_USERNAME`: MQTT username
- `DSMR_MQTT_PASSWORD`: MQTT password
- `DSMR_MQTT_TLS`: Enable TLS (set to any value to enable)
- `DSMR_VERBOSE`: Enable verbose logging (set to any value to enable)

Environment variables take precedence over command-line flags.

## MQTT Topics

| Topic               | Retained | Payload                   |
| ------------------- | -------- | ------------------------- |
| `dsmr/raw/telegram` | No       | Full DSMR telegram text   |
| `dsmr/raw/latest`   | Yes      | Most recent full telegram |
| `dsmr/status`       | Yes      | `online` / `offline`      |

All topics use QoS 1. The `dsmr/status` topic uses Last Will and Testament to publish `offline` if the connection is lost unexpectedly.

## Security Features

The application includes several security features:

- **Input Validation**: All configuration values are validated to prevent injection attacks
- **TLS Support**: Secure MQTT connections with TLS 1.2+ and certificate verification
- **Resource Limits**: Protection against DoS attacks with buffer and size limits
  - Maximum 200 lines per telegram
  - Maximum 10KB per telegram
  - Maximum 1KB per line
- **Path Validation**: Serial device paths are validated to prevent path traversal attacks
- **MQTT Spec Compliance**: Client IDs validated per MQTT 3.1.1 specification

### Using TLS

TLS can be enabled in several ways:

1. **Via URL scheme** (automatic):
   ```bash
   -mqtt-broker ssl://mqtt.example.com:8883
   # or
   -mqtt-broker tls://mqtt.example.com:8883
   ```

2. **Via flag**:
   ```bash
   -mqtt-broker tcp://mqtt.example.com:8883 -mqtt-tls
   ```

3. **Via environment variable**:
   ```bash
   export DSMR_MQTT_TLS=1
   export DSMR_MQTT_BROKER=tcp://mqtt.example.com:8883
   ```

**Note**: For production deployments, always use TLS to encrypt credentials and data in transit.

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

