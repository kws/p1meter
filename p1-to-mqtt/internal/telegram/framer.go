package telegram

import (
	"fmt"
	"strings"
)

const (
	// MaxBufferLines is the maximum number of lines in a telegram buffer
	// DSMR telegrams typically have 20-30 lines, so 200 is a generous limit
	MaxBufferLines = 200
	// MaxTelegramSize is the maximum size of a complete telegram in bytes
	// DSMR telegrams are typically 1-2KB, so 10KB is a generous limit
	MaxTelegramSize = 10 * 1024
	// MaxLineLength is the maximum length of a single line
	MaxLineLength = 1024
)

// Framer handles framing of DSMR telegrams
type Framer struct {
	buffer    []string
	inFrame   bool
	totalSize int // Track total size of buffered data
}

// NewFramer creates a new telegram framer
func NewFramer() *Framer {
	return &Framer{
		buffer:    make([]string, 0, 50),
		inFrame:   false,
		totalSize: 0,
	}
}

// ProcessLine processes a line and returns a complete telegram if one is detected.
// Returns the telegram as a string (with newlines) and true if complete,
// or empty string and false if not yet complete.
// Returns an error message if limits are exceeded.
func (f *Framer) ProcessLine(line string) (string, bool, error) {
	// Validate line length
	if len(line) > MaxLineLength {
		return "", false, fmt.Errorf("line too long: %d bytes (max %d)", len(line), MaxLineLength)
	}

	line = strings.TrimSpace(line)

	// Check for start marker
	if strings.HasPrefix(line, "/") {
		f.buffer = []string{line}
		f.inFrame = true
		f.totalSize = len(line)
		return "", false, nil
	}

	// If not in a frame, ignore the line
	if !f.inFrame {
		return "", false, nil
	}

	// Check buffer size limits
	if len(f.buffer) >= MaxBufferLines {
		// Reset buffer to prevent DoS
		f.buffer = nil
		f.inFrame = false
		f.totalSize = 0
		return "", false, fmt.Errorf("telegram buffer exceeded maximum lines (%d), resetting", MaxBufferLines)
	}

	// Check total size limit
	lineSize := len(line) + 1 // +1 for newline
	if f.totalSize+lineSize > MaxTelegramSize {
		// Reset buffer to prevent DoS
		f.buffer = nil
		f.inFrame = false
		f.totalSize = 0
		return "", false, fmt.Errorf("telegram size exceeded maximum (%d bytes), resetting", MaxTelegramSize)
	}

	// Add line to buffer
	f.buffer = append(f.buffer, line)
	f.totalSize += lineSize

	// Check for end marker
	if strings.HasPrefix(line, "!") {
		// Complete telegram
		telegram := strings.Join(f.buffer, "\n") + "\n"
		telegramSize := len(telegram)
		
		// Final size check
		if telegramSize > MaxTelegramSize {
			f.buffer = nil
			f.inFrame = false
			f.totalSize = 0
			return "", false, fmt.Errorf("complete telegram exceeded maximum size (%d bytes)", MaxTelegramSize)
		}

		f.buffer = nil
		f.inFrame = false
		f.totalSize = 0
		return telegram, true, nil
	}

	return "", false, nil
}

