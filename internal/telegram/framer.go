package telegram

import (
	"strings"
)

// Framer handles framing of DSMR telegrams
type Framer struct {
	buffer    []string
	inFrame   bool
}

// NewFramer creates a new telegram framer
func NewFramer() *Framer {
	return &Framer{
		buffer:  make([]string, 0, 50),
		inFrame: false,
	}
}

// ProcessLine processes a line and returns a complete telegram if one is detected.
// Returns the telegram as a string (with newlines) and true if complete,
// or empty string and false if not yet complete.
func (f *Framer) ProcessLine(line string) (string, bool) {
	line = strings.TrimSpace(line)

	// Check for start marker
	if strings.HasPrefix(line, "/") {
		f.buffer = []string{line}
		f.inFrame = true
		return "", false
	}

	// If not in a frame, ignore the line
	if !f.inFrame {
		return "", false
	}

	// Add line to buffer
	f.buffer = append(f.buffer, line)

	// Check for end marker
	if strings.HasPrefix(line, "!") {
		// Complete telegram
		telegram := strings.Join(f.buffer, "\n") + "\n"
		f.buffer = nil
		f.inFrame = false
		return telegram, true
	}

	return "", false
}

