package mqtt

import (
	"crypto/tls"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

const (
	topicTelegram = "dsmr/raw/telegram"
	topicStatus   = "dsmr/status"
)

// Publisher handles MQTT publishing with auto-reconnect
type Publisher struct {
	broker   string
	clientID string
	username string
	password string
	useTLS   bool
	client   mqtt.Client
	queue    chan string
	wg       sync.WaitGroup
	mu       sync.Mutex
	verbose  bool
}

// NewPublisher creates a new MQTT publisher
func NewPublisher(broker, clientID, username, password string, useTLS bool, verbose bool) *Publisher {
	return &Publisher{
		broker:   broker,
		clientID: clientID,
		username: username,
		password: password,
		useTLS:   useTLS,
		queue:    make(chan string, 100),
		verbose:  verbose,
	}
}

// Start begins the publisher and connects to MQTT broker
func (p *Publisher) Start() error {
	if err := p.connect(); err != nil {
		return err
	}

	p.wg.Add(1)
	go p.publishLoop()

	return nil
}

// PublishTelegram queues a telegram for publishing
func (p *Publisher) PublishTelegram(telegram string) {
	select {
	case p.queue <- telegram:
	default:
		log.Printf("Warning: MQTT queue full, dropping telegram")
	}
}

// PublishStatus publishes the status (online/offline)
func (p *Publisher) PublishStatus(status string) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.client == nil || !p.client.IsConnected() {
		return fmt.Errorf("MQTT client not connected")
	}

	token := p.client.Publish(topicStatus, 1, true, status)
	token.Wait()
	return token.Error()
}

// Stop stops the publisher and disconnects
func (p *Publisher) Stop() {
	close(p.queue)
	p.wg.Wait()

	p.mu.Lock()
	if p.client != nil && p.client.IsConnected() {
		p.client.Disconnect(250)
	}
	p.mu.Unlock()
}

func (p *Publisher) connect() error {
	if p.verbose {
		log.Printf("Connecting to MQTT broker: %s (client ID: %s)", p.broker, p.clientID)
	}

	// Determine if TLS should be used based on URL scheme or explicit flag
	brokerURL := p.broker
	useTLS := p.useTLS

	// Check URL scheme for TLS indication
	if strings.HasPrefix(strings.ToLower(brokerURL), "ssl://") ||
		strings.HasPrefix(strings.ToLower(brokerURL), "tls://") ||
		strings.HasPrefix(strings.ToLower(brokerURL), "wss://") {
		useTLS = true
		// Convert ssl:// to tcp:// for the broker URL (TLS is configured separately)
		brokerURL = strings.Replace(brokerURL, "ssl://", "tcp://", 1)
		brokerURL = strings.Replace(brokerURL, "tls://", "tcp://", 1)
		brokerURL = strings.Replace(brokerURL, "wss://", "ws://", 1)
	}

	opts := mqtt.NewClientOptions()
	opts.AddBroker(brokerURL)
	opts.SetClientID(p.clientID)
	opts.SetCleanSession(true)
	opts.SetAutoReconnect(true)
	opts.SetConnectRetry(true)
	opts.SetConnectRetryInterval(5 * time.Second)
	opts.SetConnectTimeout(10 * time.Second)
	opts.SetPingTimeout(10 * time.Second)
	opts.SetWriteTimeout(10 * time.Second)

	// Configure TLS if enabled
	if useTLS {
		tlsConfig := &tls.Config{
			InsecureSkipVerify: false, // Verify server certificate by default
			MinVersion:         tls.VersionTLS12,
		}
		opts.SetTLSConfig(tlsConfig)
		if p.verbose {
			log.Println("TLS enabled for MQTT connection")
		}
	} else {
		if p.verbose {
			log.Println("Warning: TLS not enabled - connection is not encrypted")
		}
	}

	// Set username and password if provided
	if p.username != "" {
		opts.SetUsername(p.username)
		if p.verbose {
			log.Printf("Using MQTT username: %s", p.username)
		}
	}
	if p.password != "" {
		opts.SetPassword(p.password)
		if p.verbose {
			log.Println("Using MQTT password: [hidden]")
		}
	}

	// Last Will and Testament
	opts.SetWill(topicStatus, "offline", 1, true)

	// Connection handler
	opts.OnConnect = func(client mqtt.Client) {
		log.Printf("Connected to MQTT broker: %s", p.broker)
		// Publish online status
		if token := client.Publish(topicStatus, 1, true, "online"); token.Wait() && token.Error() != nil {
			log.Printf("Failed to publish online status: %v", token.Error())
		} else if p.verbose {
			log.Println("Published 'online' status to MQTT")
		}
	}

	opts.OnConnectionLost = func(client mqtt.Client, err error) {
		log.Printf("MQTT connection lost: %v", err)
	}

	client := mqtt.NewClient(opts)
	token := client.Connect()

	// Wait for connection with timeout
	if !token.WaitTimeout(15 * time.Second) {
		return fmt.Errorf("connection timeout: failed to connect to MQTT broker %s within 15 seconds", p.broker)
	}

	if err := token.Error(); err != nil {
		return fmt.Errorf("failed to connect to MQTT broker %s: %w", p.broker, err)
	}

	p.mu.Lock()
	p.client = client
	p.mu.Unlock()

	return nil
}

func (p *Publisher) publishLoop() {
	defer p.wg.Done()

	for telegram := range p.queue {
		p.mu.Lock()
		client := p.client
		connected := client != nil && client.IsConnected()
		p.mu.Unlock()

		if !connected {
			log.Printf("MQTT not connected, attempting reconnect...")
			if err := p.connect(); err != nil {
				log.Printf("Failed to reconnect: %v", err)
				time.Sleep(5 * time.Second)
				continue
			}
			// Get the client again after reconnection
			p.mu.Lock()
			client = p.client
			p.mu.Unlock()
		}

		// Validate telegram size before publishing (safety check)
		if len(telegram) > 10*1024 {
			log.Printf("Warning: Telegram size (%d bytes) exceeds recommended limit, publishing anyway", len(telegram))
		}

		// Publish to telegram topic (not retained)
		token := client.Publish(topicTelegram, 1, false, telegram)
		token.Wait()
		if err := token.Error(); err != nil {
			log.Printf("Failed to publish telegram to %s: %v", topicTelegram, err)
			continue
		}
		if p.verbose {
			log.Printf("Published telegram to %s (%d bytes)", topicTelegram, len(telegram))
		}

	}
}
