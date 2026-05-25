.PHONY: build build-pi clean

BINARY_NAME=dsmr-mqtt
BUILD_DIR=bin

# Default target
build:
	@echo "Building for local platform..."
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/dsmr-mqtt

# Cross-compile for Raspberry Pi (ARM64)
build-pi:
	@echo "Cross-compiling for Raspberry Pi (linux/arm64)..."
	@mkdir -p $(BUILD_DIR)
	GOOS=linux GOARCH=arm64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64 ./cmd/dsmr-mqtt

# Cross-compile for Raspberry Pi (ARM32)
build-pi32:
	@echo "Cross-compiling for Raspberry Pi (linux/arm)..."
	@mkdir -p $(BUILD_DIR)
	GOOS=linux GOARCH=arm go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm ./cmd/dsmr-mqtt

clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)

