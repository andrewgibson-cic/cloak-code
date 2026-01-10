package main

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
)

// LoadConfig loads and parses the sidecar.json configuration file
func LoadConfig(configPath string) (*Config, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config JSON: %w", err)
	}

	// Set default port if not specified
	if config.Port == 0 {
		config.Port = 8888
	}

	// Set default env file if not specified
	if config.EnvFile == "" {
		config.EnvFile = ".env.vault"
	}

	return &config, nil
}

// LoadEnvFile loads environment variables from a .env file
func LoadEnvFile(envFilePath string) (map[string]string, error) {
	data, err := os.ReadFile(envFilePath)
	if err != nil {
		// If the file doesn't exist, return empty map (optional feature)
		if os.IsNotExist(err) {
			return make(map[string]string), nil
		}
		return nil, fmt.Errorf("failed to read env file: %w", err)
	}

	env := make(map[string]string)
	lines := strings.Split(string(data), "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)

		// Skip empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Parse KEY=VALUE format
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])

		// Remove quotes if present
		value = strings.Trim(value, "\"'")

		env[key] = value
	}

	return env, nil
}

// ExpandVariables replaces ${VAR_NAME} placeholders in a string with actual values from env
func ExpandVariables(input string, env map[string]string) string {
	re := regexp.MustCompile(`\$\{([^}]+)\}`)
	return re.ReplaceAllStringFunc(input, func(match string) string {
		// Remove ${ and }
		varName := match[2 : len(match)-1]
		if value, exists := env[varName]; exists {
			return value
		}
		// If variable not found, return empty string (or could return the original)
		return ""
	})
}

// ExpandRouteHeaders expands all headers in a route using environment variables
func (ps *ProxyServer) expandRouteHeaders(route *Route) map[string]string {
	expanded := make(map[string]string)
	for key, value := range route.Headers {
		expanded[key] = ExpandVariables(value, ps.env)
	}
	return expanded
}
