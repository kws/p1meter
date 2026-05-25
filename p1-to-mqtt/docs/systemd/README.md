# Systemd Service Installation

This guide describes the intended systemd deployment for the DSMR MQTT bridge on
the Raspberry Pi attached to the smart meter.

The target state is to install the cross-compiled binary as a service, keep
MQTT credentials out of the process list, and use the stable P1 USB serial
symlink instead of `/dev/ttyUSB0`.

## Files

- `dsmr-mqtt.service`: example unit file.
- `dsmr-mqtt.conf.example`: environment file template.

## Install

Build the Pi binary from `p1-to-mqtt/`:

```bash
make build-pi
```

Copy the binary and service files to the Pi:

```bash
sudo install -m 0755 bin/dsmr-mqtt-linux-arm64 /usr/local/bin/dsmr-mqtt
sudo install -m 0644 docs/systemd/dsmr-mqtt.service /etc/systemd/system/dsmr-mqtt.service
sudo install -m 0600 docs/systemd/dsmr-mqtt.conf.example /etc/dsmr-mqtt.conf
```

Edit `/etc/dsmr-mqtt.conf` and set the real MQTT credentials. Prefer a stable
serial symlink like:

```text
/dev/serial/by-id/usb-FTDI_P1_CABLE-if00-port0
```

Create the service user if it does not exist, and grant serial access:

```bash
sudo useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin dsmr
sudo usermod -a -G dialout dsmr
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dsmr-mqtt
```

## Verify

```bash
systemctl status dsmr-mqtt
journalctl -u dsmr-mqtt -n 100
```

The bridge should publish:

- `dsmr/status`: retained `online` / `offline`.
- `dsmr/raw/telegram`: raw DSMR telegrams for the Python decoder.

## Troubleshooting

Check serial device access:

```bash
ls -l /dev/serial/by-id/
id dsmr
```

Check broker connectivity:

```bash
getent hosts mqtt-broker.local
nc -vz mqtt-broker.local 1883
```

Temporarily set `DSMR_VERBOSE=1` in `/etc/dsmr-mqtt.conf` for more detailed
journal output.
