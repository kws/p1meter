package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/kws/p1-to-mqtt/internal/config"
	"github.com/kws/p1-to-mqtt/internal/mqtt"
	"github.com/kws/p1-to-mqtt/internal/serial"
	"github.com/kws/p1-to-mqtt/internal/telegram"
)

func main() {
	if os.Getenv("DSMR_VERBOSE") != "" {
		log.SetFlags(log.LstdFlags | log.Lshortfile)
	} else {
		log.SetFlags(log.LstdFlags)
	}

	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Configuration error: %v", err)
	}

	if cfg.Verbose {
		log.Println("Starting DSMR to MQTT bridge...")
		log.Printf("Configuration loaded:")
		log.Printf("  Serial device: %s", cfg.SerialDevice)
		log.Printf("  MQTT broker: %s", cfg.MQTTBroker)
		log.Printf("  MQTT client ID: %s", cfg.MQTTClientID)
		if cfg.MQTTUsername != "" {
			log.Printf("  MQTT username: %s", cfg.MQTTUsername)
		}
	}

	// Initialize components
	serialReader := serial.NewReader(cfg.SerialDevice, cfg.Verbose)
	mqttPublisher := mqtt.NewPublisher(cfg.MQTTBroker, cfg.MQTTClientID, cfg.MQTTUsername, cfg.MQTTPassword, cfg.MQTTTLS, cfg.Verbose)
	telegramFramer := telegram.NewFramer()

	// Start MQTT publisher
	if cfg.Verbose {
		log.Println("Connecting to MQTT broker...")
	}
	if err := mqttPublisher.Start(); err != nil {
		log.Fatalf("Failed to start MQTT publisher: %v", err)
	}

	// Start serial reader
	if cfg.Verbose {
		log.Printf("Starting serial reader on %s...", cfg.SerialDevice)
	}
	serialReader.Start()
	if cfg.Verbose {
		log.Println("Bridge started, waiting for data...")
	}

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Main processing loop
	go func() {
		for {
			select {
			case line, ok := <-serialReader.Lines():
				if !ok {
					if cfg.Verbose {
						log.Println("Serial lines channel closed")
					}
					return
				}
				if cfg.Verbose {
					log.Printf("Received line: %s", line)
				}
				telegram, complete, err := telegramFramer.ProcessLine(line)
				if err != nil {
					log.Printf("Telegram framing error: %v", err)
					continue
				}
				if complete {
					if cfg.Verbose {
						log.Printf("Complete telegram detected (%d bytes), publishing to MQTT...", len(telegram))
					}
					mqttPublisher.PublishTelegram(telegram)
					if cfg.Verbose {
						log.Println("Telegram published to MQTT")
					}
				}
			case err := <-serialReader.Errors():
				if err != nil {
					log.Printf("Serial error: %v", err)
				}
			}
		}
	}()

	// Wait for shutdown signal
	<-sigChan
	log.Println("Shutting down...")

	// Publish offline status
	if err := mqttPublisher.PublishStatus("offline"); err != nil {
		log.Printf("Failed to publish offline status: %v", err)
	}

	// Stop components
	serialReader.Stop()
	mqttPublisher.Stop()

	log.Println("Shutdown complete")
}
