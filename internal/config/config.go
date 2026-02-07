package config

import (
	"flag"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"unicode"
)

const (
	// MaxConfigValueLength is the maximum length for configuration values
	MaxConfigValueLength = 512
	// MaxClientIDLength is the maximum length for MQTT client ID (MQTT 3.1.1 spec limit is 23)
	MaxClientIDLength = 23
)

// Config holds all configuration for the application
type Config struct {
	SerialDevice string
	MQTTBroker   string
	MQTTClientID string
	MQTTUsername string
	MQTTPassword string
	MQTTTLS      bool
	Verbose      bool
}

// Load reads configuration from command-line flags and environment variables.
// Environment variables take precedence over flags.
// Returns an error if required configuration is missing or invalid.
func Load() (*Config, error) {
	cfg := &Config{}

	// Define flags with defaults
	flag.StringVar(&cfg.SerialDevice, "serial-device", "/dev/ttyUSB0", "Serial device path (DSMR_SERIAL_DEVICE)")
	flag.StringVar(&cfg.MQTTBroker, "mqtt-broker", "", "MQTT broker URL (DSMR_MQTT_BROKER)")
	flag.StringVar(&cfg.MQTTClientID, "mqtt-client-id", "", "MQTT client ID (DSMR_MQTT_CLIENT_ID)")
	flag.StringVar(&cfg.MQTTUsername, "mqtt-username", "", "MQTT username (DSMR_MQTT_USERNAME)")
	flag.StringVar(&cfg.MQTTPassword, "mqtt-password", "", "MQTT password (DSMR_MQTT_PASSWORD)")
	flag.BoolVar(&cfg.MQTTTLS, "mqtt-tls", false, "Enable TLS for MQTT connection (DSMR_MQTT_TLS)")
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
	if os.Getenv("DSMR_MQTT_TLS") != "" {
		cfg.MQTTTLS = true
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

	// Validate configuration values
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("configuration validation failed: %w", err)
	}

	return cfg, nil
}

// validate performs security validation on all configuration values
func (c *Config) validate() error {
	// Validate serial device path
	if err := c.validateSerialDevice(); err != nil {
		return fmt.Errorf("serial device: %w", err)
	}

	// Validate MQTT broker URL
	if err := c.validateMQTTBroker(); err != nil {
		return fmt.Errorf("mqtt broker: %w", err)
	}

	// Validate MQTT client ID
	if err := c.validateMQTTClientID(); err != nil {
		return fmt.Errorf("mqtt client ID: %w", err)
	}

	// Validate MQTT username
	if len(c.MQTTUsername) > MaxConfigValueLength {
		return fmt.Errorf("mqtt username too long: %d bytes (max %d)", len(c.MQTTUsername), MaxConfigValueLength)
	}

	// Validate MQTT password
	if len(c.MQTTPassword) > MaxConfigValueLength {
		return fmt.Errorf("mqtt password too long: %d bytes (max %d)", len(c.MQTTPassword), MaxConfigValueLength)
	}

	return nil
}

// validateSerialDevice validates the serial device path to prevent path traversal
func (c *Config) validateSerialDevice() error {
	if len(c.SerialDevice) == 0 {
		return fmt.Errorf("serial device path cannot be empty")
	}
	if len(c.SerialDevice) > MaxConfigValueLength {
		return fmt.Errorf("serial device path too long: %d bytes (max %d)", len(c.SerialDevice), MaxConfigValueLength)
	}

	// Prevent path traversal attacks
	cleanPath := filepath.Clean(c.SerialDevice)
	if cleanPath != c.SerialDevice && !strings.HasPrefix(c.SerialDevice, "/dev/") {
		return fmt.Errorf("serial device path contains invalid characters: %s", c.SerialDevice)
	}

	// Ensure it's a device path (starts with /dev/ on Unix)
	if !strings.HasPrefix(c.SerialDevice, "/dev/") && !strings.HasPrefix(c.SerialDevice, "COM") {
		return fmt.Errorf("serial device path must be a valid device path (e.g., /dev/ttyUSB0)")
	}

	return nil
}

// validateMQTTBroker validates the MQTT broker URL
func (c *Config) validateMQTTBroker() error {
	if len(c.MQTTBroker) == 0 {
		return fmt.Errorf("mqtt broker URL cannot be empty")
	}
	if len(c.MQTTBroker) > MaxConfigValueLength {
		return fmt.Errorf("mqtt broker URL too long: %d bytes (max %d)", len(c.MQTTBroker), MaxConfigValueLength)
	}

	// Parse URL to validate format
	parsedURL, err := url.Parse(c.MQTTBroker)
	if err != nil {
		return fmt.Errorf("invalid URL format: %w", err)
	}

	// Validate scheme
	scheme := strings.ToLower(parsedURL.Scheme)
	validSchemes := []string{"tcp", "ssl", "tls", "ws", "wss"}
	valid := false
	for _, s := range validSchemes {
		if scheme == s {
			valid = true
			break
		}
	}
	if !valid {
		return fmt.Errorf("invalid URL scheme: %s (valid: %v)", scheme, validSchemes)
	}

	// Warn if using plain TCP without TLS
	if (scheme == "tcp" || scheme == "ws") && !c.MQTTTLS {
		// This is a warning, not an error, as localhost connections may be acceptable
		// But we log it for security awareness
		if c.Verbose {
			fmt.Fprintf(os.Stderr, "Warning: Using plain TCP without TLS. Consider using ssl:// or tls:// scheme, or enable -mqtt-tls\n")
		}
	}

	return nil
}

// validateMQTTClientID validates the MQTT client ID according to MQTT spec
func (c *Config) validateMQTTClientID() error {
	if len(c.MQTTClientID) == 0 {
		return fmt.Errorf("mqtt client ID cannot be empty")
	}
	if len(c.MQTTClientID) > MaxClientIDLength {
		return fmt.Errorf("mqtt client ID too long: %d bytes (max %d per MQTT 3.1.1 spec)", len(c.MQTTClientID), MaxClientIDLength)
	}

	// MQTT client ID must contain only printable characters (0x20-0x7E)
	// and cannot contain wildcards (#, +)
	for _, r := range c.MQTTClientID {
		if !unicode.IsPrint(r) {
			return fmt.Errorf("mqtt client ID contains non-printable character: %q", r)
		}
		if r == '#' || r == '+' {
			return fmt.Errorf("mqtt client ID cannot contain wildcard characters (#, +)")
		}
	}

	return nil
}

