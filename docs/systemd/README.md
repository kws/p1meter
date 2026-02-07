# Systemd Service Installation

This guide explains how to install and configure the DSMR MQTT bridge as a systemd service on your Raspberry Pi.

## Prerequisites

1. The binary `dsmr-mqtt-linux-arm64` should be located at `/home/pi/p1/dsmr-mqtt-linux-arm64`
2. The serial device should be accessible at `/dev/ttyUSB0`
3. Network connectivity to your MQTT broker

## Installation Steps

### 1. Copy the binary to the Raspberry Pi

```bash
# From your development machine
scp bin/dsmr-mqtt-linux-arm64 pi@raspberrypi.local:p1/
ssh pi@raspberrypi.local "chmod +x ~/p1/dsmr-mqtt-linux-arm64"
```

### 2. Create the configuration file

```bash
# On the Raspberry Pi
sudo cp dsmr-mqtt.conf.example /etc/dsmr-mqtt.conf
sudo nano /etc/dsmr-mqtt.conf
```

Edit the file and set your MQTT password:
```
DSMR_MQTT_PASSWORD=your_actual_password_here
```

Secure the configuration file:
```bash
sudo chmod 600 /etc/dsmr-mqtt.conf
```

### 3. Install the service file

```bash
# Copy the service file to systemd directory
sudo cp dsmr-mqtt.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload
```

### 4. Edit the service file (if needed)

You may need to adjust paths or settings in the service file:

```bash
sudo nano /etc/systemd/system/dsmr-mqtt.service
```

Common adjustments:
- Change the binary path if it's not at `/home/pi/p1/dsmr-mqtt-linux-arm64`
- Change the serial device if it's not `/dev/ttyUSB0`
- Update MQTT broker URL, client ID, or username
- Adjust the user/group if not running as `pi`

After editing, reload systemd:
```bash
sudo systemctl daemon-reload
```

### 5. Enable and start the service

```bash
# Enable the service to start on boot
sudo systemctl enable dsmr-mqtt

# Start the service now
sudo systemctl start dsmr-mqtt
```

### 6. Verify the service is running

```bash
# Check service status
sudo systemctl status dsmr-mqtt

# View recent logs
sudo journalctl -u dsmr-mqtt -f

# View logs from the last 50 lines
sudo journalctl -u dsmr-mqtt -n 50
```

## Service Management

### Start/Stop/Restart

```bash
sudo systemctl start dsmr-mqtt
sudo systemctl stop dsmr-mqtt
sudo systemctl restart dsmr-mqtt
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u dsmr-mqtt -f

# View logs from today
sudo journalctl -u dsmr-mqtt --since today

# View last 100 lines
sudo journalctl -u dsmr-mqtt -n 100
```

### Check Status

```bash
# Detailed status
sudo systemctl status dsmr-mqtt

# Quick check if running
systemctl is-active dsmr-mqtt
```

## Troubleshooting

### Service fails to start

1. Check the service status:
   ```bash
   sudo systemctl status dsmr-mqtt
   ```

2. Check logs for errors:
   ```bash
   sudo journalctl -u dsmr-mqtt -n 50
   ```

3. Verify the binary exists and is executable:
   ```bash
   ls -l /home/pi/p1/dsmr-mqtt-linux-arm64
   ```

4. Test the binary manually:
   ```bash
   /home/pi/p1/dsmr-mqtt-linux-arm64 -mqtt-broker tcp://localhost:1883 -mqtt-client-id test -mqtt-username mqttuser -mqtt-password yourpass
   ```

### Serial device not found

If `/dev/ttyUSB0` doesn't exist:
1. Check available serial devices: `ls -l /dev/ttyUSB*`
2. Update the service file with the correct device path
3. Ensure the `pi` user is in the `dialout` group:
   ```bash
   sudo usermod -a -G dialout pi
   ```
   (Requires logout/login to take effect)

### MQTT connection issues

1. Verify network connectivity:
   ```bash
   ping your-mqtt-broker-hostname
   telnet your-mqtt-broker-hostname 1883
   ```

2. Check MQTT credentials in `/etc/dsmr-mqtt.conf`

3. Enable verbose logging temporarily by adding to the service file:
   ```
   Environment="DSMR_VERBOSE=1"
   ```

## Service Configuration

The service is configured with:
- **Auto-restart**: The service will automatically restart if it crashes
- **Restart delay**: 10 seconds between restart attempts
- **Logging**: All output goes to systemd journal
- **Security**: Runs with limited privileges (NoNewPrivileges, PrivateTmp)
- **Network dependency**: Waits for network to be online before starting

## Uninstallation

To remove the service:

```bash
# Stop and disable the service
sudo systemctl stop dsmr-mqtt
sudo systemctl disable dsmr-mqtt

# Remove the service file
sudo rm /etc/systemd/system/dsmr-mqtt.service

# Remove the configuration file (optional)
sudo rm /etc/dsmr-mqtt.conf

# Reload systemd
sudo systemctl daemon-reload
```

