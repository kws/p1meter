package serial

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"time"

	"go.bug.st/serial"
)

// Reader handles reading from a serial port with retry logic
type Reader struct {
	device   string
	port     serial.Port
	scanner  *bufio.Scanner
	lines    chan string
	errors   chan error
	ctx      context.Context
	cancel   context.CancelFunc
	verbose  bool
}

// NewReader creates a new serial reader
func NewReader(device string, verbose bool) *Reader {
	ctx, cancel := context.WithCancel(context.Background())
	return &Reader{
		device:  device,
		lines:   make(chan string, 100),
		errors:  make(chan error, 10),
		ctx:     ctx,
		cancel:  cancel,
		verbose: verbose,
	}
}

// Lines returns a channel that receives lines from the serial port
func (r *Reader) Lines() <-chan string {
	return r.lines
}

// Errors returns a channel that receives errors from the serial port
func (r *Reader) Errors() <-chan error {
	return r.errors
}

// Start begins reading from the serial port with retry logic
func (r *Reader) Start() {
	go r.readLoop()
}

// Stop closes the serial port and stops reading
func (r *Reader) Stop() {
	r.cancel()
	if r.port != nil {
		r.port.Close()
	}
	close(r.lines)
	close(r.errors)
}

func (r *Reader) readLoop() {
	backoff := time.Second
	maxBackoff := 30 * time.Second

	for {
		select {
		case <-r.ctx.Done():
			return
		default:
		}

		err := r.connect()
		if err != nil {
			log.Printf("Failed to connect to serial device %s: %v (retrying in %v)", r.device, err, backoff)
			time.Sleep(backoff)
			backoff = min(backoff*2, maxBackoff)
			continue
		}

		// Reset backoff on successful connection
		backoff = time.Second
		if r.verbose {
			log.Println("Serial connection established, waiting for data...")
		}

		// Read lines until error or context cancellation
		for {
			select {
			case <-r.ctx.Done():
				return
			default:
			}

			if !r.scanner.Scan() {
				if err := r.scanner.Err(); err != nil {
					log.Printf("Serial read error: %v", err)
					r.errors <- err
				} else {
					log.Println("Serial scanner reached EOF, connection may be lost")
				}
				// Connection lost, break to reconnect
				if r.port != nil {
					r.port.Close()
					r.port = nil
				}
				break
			}

			line := r.scanner.Text()
			select {
			case r.lines <- line:
			case <-r.ctx.Done():
				return
			}
		}
	}
}

func (r *Reader) connect() error {
	if r.port != nil {
		return nil
	}

	if r.verbose {
		log.Printf("Attempting to open serial device: %s", r.device)
	}
	mode := &serial.Mode{
		BaudRate: 115200,
		DataBits: 8,
		Parity:   serial.NoParity,
		StopBits: serial.OneStopBit,
	}

	port, err := serial.Open(r.device, mode)
	if err != nil {
		return fmt.Errorf("failed to open serial port: %w", err)
	}

	r.port = port
	r.scanner = bufio.NewScanner(port)
	if r.verbose {
		log.Printf("Successfully opened serial device: %s", r.device)
	}
	return nil
}

