package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"sort"
	"strings"
)

func main() {
	// CLI flags
	configPath := flag.String("config", "sidecar.json", "Path to the sidecar configuration file")
	port := flag.Int("port", 0, "Port to listen on (overrides config file)")
	unsafe := flag.Bool("unsafe", false, "Allow binding to 0.0.0.0 (unsafe, not recommended)")
	verbose := flag.Bool("verbose", false, "Enable verbose debug logging")
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

	// Load environment variables
	env, err := LoadEnvFile(config.EnvFile)
	if err != nil {
		log.Fatalf("Failed to load env file: %v", err)
	}
	if *verbose {
		log.Printf("Loaded %d environment variables from %s", len(env), config.EnvFile)
	}

	// Create proxy server
	proxyServer := &ProxyServer{
		config:  config,
		env:     env,
		routes:  make(map[string]*ProxyRoute),
		verbose: *verbose,
	}

	// Expand and prepare routes
	for path, route := range config.Routes {
		expandedHeaders := make(map[string]string)
		for key, value := range route.Headers {
			expandedValue := ExpandVariables(value, env)
			expandedHeaders[key] = expandedValue

			// Debug: Log whether variable expansion succeeded (without exposing values)
			if *verbose && strings.Contains(value, "${") {
				if expandedValue == "" {
					log.Printf("WARNING: Route %s header %s: variable expansion FAILED for template '%s'", path, key, value)
				} else {
					log.Printf("Route %s header %s: variable expanded successfully from template '%s'", path, key, value)
				}
			}
		}

		proxyServer.routes[path] = &ProxyRoute{
			Target:  route.Target,
			Headers: expandedHeaders,
		}
	}

	// Setup HTTP handler
	http.HandleFunc("/", proxyServer.handleRequest)

	// Determine bind address
	bindAddr := "127.0.0.1"
	if *unsafe {
		bindAddr = "0.0.0.0"
	}

	// Print startup banner
	printBanner(bindAddr, config.Port, proxyServer.routes, isWSL2())

	// Start server
	addr := fmt.Sprintf("%s:%d", bindAddr, config.Port)
	log.Printf("Starting server on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}

func printBanner(bindAddr string, port int, routes map[string]*ProxyRoute, wslIP string) {
	fmt.Printf("🛡️  env-sidecar running on %s:%d\n", bindAddr, port)
	fmt.Println(strings.Repeat("-", 40))

	if len(routes) > 0 {
		fmt.Println("Proxy Maps:")

		// Sort routes for consistent output
		var routePaths []string
		for path := range routes {
			routePaths = append(routePaths, path)
		}
		sort.Strings(routePaths)

		for _, path := range routePaths {
			route := routes[path]
			fmt.Printf("  %s  -> %s\n", path, route.Target)
		}
		fmt.Println()
	}

	// Extract unique base URLs for AI instructions
	fmt.Println("👉 Instructions for AI:")
	var baseURLs []string
	seenTargets := make(map[string]bool)

	// Add localhost URL (for local access)
	for path, route := range routes {
		target := route.Target
		if !seenTargets[target] {
			baseURLs = append(baseURLs, fmt.Sprintf("Set your Base URL to http://127.0.0.1:%d%s", port, path))
			seenTargets[target] = true
		}
	}

	// If running in WSL2 with 0.0.0.0, also show WSL IP and host.docker.internal
	if wslIP != "" && bindAddr == "0.0.0.0" {
		for path := range routes {
			baseURLs = append(baseURLs, fmt.Sprintf("  (from Docker): http://host.docker.internal:%d%s", port, path))
			baseURLs = append(baseURLs, fmt.Sprintf("  (from Docker): http://%s:%d%s", wslIP, port, path))
			break // Only show once
		}
	}

	for _, instruction := range baseURLs {
		fmt.Printf("  \"%s\"\n", instruction)
	}
	fmt.Println()
}

// isWSL2 detects if running in WSL2 and returns the WSL2 IP address
func isWSL2() string {
	// Check for WSL2 indicator file
	if _, err := os.Stat("/proc/version"); err == nil {
		content, err := os.ReadFile("/proc/version")
		if err == nil && strings.Contains(string(content), "microsoft") {
			// Get WSL2 IP address
			interfaces, err := net.Interfaces()
			if err != nil {
				return ""
			}
			for _, iface := range interfaces {
				if iface.Name == "eth0" {
					addrs, err := iface.Addrs()
					if err != nil {
						continue
					}
					for _, addr := range addrs {
						if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
							if ipnet.IP.To4() != nil {
								return ipnet.IP.String()
							}
						}
					}
				}
			}
		}
	}
	return ""
}
