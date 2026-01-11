package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"sort"
	"strings"
)

func main() {
	// CLI flags
	configPath := flag.String("config", "sidecar.json", "Path to the sidecar configuration file")
	port := flag.Int("port", 0, "Port to listen on (overrides config file)")
	verbose := flag.Bool("verbose", false, "Enable verbose debug logging")
	generateCA := flag.Bool("generate-ca", false, "Generate CA certificate and exit")
	flag.Parse()

	// Load configuration
	config, err := LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Override port if specified via CLI
	if *port != 0 {
		config.Port = *port
	}

	// Set default port if not specified
	if config.Port == 0 {
		config.Port = 8080
	}

	// Set default CA paths if not specified
	if config.CA.CertPath == "" {
		config.CA.CertPath = "certs/ca.crt"
	}
	if config.CA.CAKeyPath == "" {
		config.CA.CAKeyPath = "certs/ca.key"
	}

	// Load environment variables
	env, err := LoadEnvFile(config.EnvFile)
	if err != nil {
		log.Fatalf("Failed to load env file: %v", err)
	}
	if *verbose {
		log.Printf("Loaded %d environment variables from %s", len(env), config.EnvFile)
	}

	// Generate CA certificate if requested
	if *generateCA {
		certDir := "certs"
		if err := os.MkdirAll(certDir, 0755); err != nil {
			log.Fatalf("Failed to create certs directory: %v", err)
		}
		if err := GenerateCA(config.CA.CertPath, config.CA.CAKeyPath); err != nil {
			log.Fatalf("Failed to generate CA: %v", err)
		}
		return
	}

	// Ensure CA certificate exists
	if err := ensureCAExists(config); err != nil {
		log.Fatalf("CA certificate error: %v", err)
	}

	// Load CA certificate
	caCertBytes, caKeyBytes, err := LoadCACert(config.CA.CertPath, config.CA.CAKeyPath)
	if err != nil {
		log.Fatalf("Failed to load CA certificate: %v", err)
	}

	// Create proxy server
	proxyServer := &ProxyServer{
		config:  config,
		env:     env,
		verbose: *verbose,
	}

	// Print startup banner
	printBanner(config, *verbose)

	// Start the transparent proxy
	log.Printf("Starting transparent proxy on port %d", config.Port)
	if err := proxyServer.StartTransparentProxy(caCertBytes, caKeyBytes); err != nil {
		log.Fatalf("Proxy failed: %v", err)
	}
}

func ensureCAExists(config *Config) error {
	// Check if CA certificate exists
	if _, err := os.Stat(config.CA.CertPath); os.IsNotExist(err) {
		// Create certs directory
		certDir := "certs"
		if err := os.MkdirAll(certDir, 0755); err != nil {
			return fmt.Errorf("failed to create certs directory: %w", err)
		}

		// Generate CA certificate
		log.Println("CA certificate not found, generating new one...")
		if err := GenerateCA(config.CA.CertPath, config.CA.CAKeyPath); err != nil {
			return fmt.Errorf("failed to generate CA: %w", err)
		}
	}
	return nil
}

func printBanner(config *Config, verbose bool) {
	fmt.Printf("🛡️  env-sidecar transparent proxy running on :%d\n", config.Port)
	fmt.Println(strings.Repeat("-", 50))

	if len(config.Domains) > 0 {
		fmt.Println("Domain Rules:")

		// Sort domains for consistent output
		var domains []string
		for domain := range config.Domains {
			domains = append(domains, domain)
		}
		sort.Strings(domains)

		for _, domain := range domains {
			rule := config.Domains[domain]
			var headers []string
			for header := range rule.InjectHeaders {
				headers = append(headers, header)
			}
			sort.Strings(headers)
			fmt.Printf("  %s\n", domain)
			for _, header := range headers {
				// Show template without exposing values
				template := rule.InjectHeaders[header]
				if verbose {
					fmt.Printf("    → %s: %s\n", header, template)
				} else {
					fmt.Printf("    → %s: ***\n", header)
				}
			}
		}
		fmt.Println()
	}

	fmt.Println("📡 Transparent Proxy Mode:")
	fmt.Println("   Configure your client to use HTTP proxy:")
	fmt.Printf("   http://127.0.0.1:%d\n", config.Port)
	fmt.Println()
	fmt.Println("🔒 CA Certificate:")
	fmt.Printf("   Location: %s\n", config.CA.CertPath)
	fmt.Println("   To install in client: curl http://mitm.it/cert/pem")
	fmt.Println()
}
