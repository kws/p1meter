package config

import (
	"flag"
	"fmt"
	"os"
)

// Config holds all configuration for the application
type Config struct {
	SerialDevice string
	MQTTBroker   string
	MQTTClientID string
	MQTTUsername string
	MQTTPassword string
	Verbose      bool
}

// Load reads configuration from command-line flags and environment variables.
// Environment variables take precedence over flags.
// Returns an error if required configuration is missing.
func Load() (*Config, error) {
	cfg := &Config{}

	// Define flags with defaults
	flag.StringVar(&cfg.SerialDevice, "serial-device", "/dev/ttyUSB0", "Serial device path (DSMR_SERIAL_DEVICE)")
	flag.StringVar(&cfg.MQTTBroker, "mqtt-broker", "", "MQTT broker URL (DSMR_MQTT_BROKER)")
	flag.StringVar(&cfg.MQTTClientID, "mqtt-client-id", "", "MQTT client ID (DSMR_MQTT_CLIENT_ID)")
	flag.StringVar(&cfg.MQTTUsername, "mqtt-username", "", "MQTT username (DSMR_MQTT_USERNAME)")
	flag.StringVar(&cfg.MQTTPassword, "mqtt-password", "", "MQTT password (DSMR_MQTT_PASSWORD)")
	flag.BoolVar(&cfg.Verbose, "verbose", false, "Enable verbose logging (DSMR_VERBOSE)")

	flag.Parse()

	// Override with environment variables if set
	if env := os.Getenv("DSMR_SERIAL_DEVICE"); env != "" {
		cfg.SerialDevice = env
	}
	if env := os.Getenv("DSMR_MQTT_BROKER"); env != "" {
		cfg.MQTTBroker = env
	}
	if env := os.Getenv("DSMR_MQTT_CLIENT_ID"); env != "" {
		cfg.MQTTClientID = env
	}
	if env := os.Getenv("DSMR_MQTT_USERNAME"); env != "" {
		cfg.MQTTUsername = env
	}
	if env := os.Getenv("DSMR_MQTT_PASSWORD"); env != "" {
		cfg.MQTTPassword = env
	}
	if os.Getenv("DSMR_VERBOSE") != "" {
		cfg.Verbose = true
	}

	// Validate required fields
	if cfg.MQTTBroker == "" {
		return nil, fmt.Errorf("mqtt-broker is required (set via flag or DSMR_MQTT_BROKER env var)")
	}
	if cfg.MQTTClientID == "" {
		return nil, fmt.Errorf("mqtt-client-id is required (set via flag or DSMR_MQTT_CLIENT_ID env var)")
	}

	return cfg, nil
}

