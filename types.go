package main

// Config represents the sidecar configuration
type Config struct {
	Port    int              `json:"port"`
	EnvFile string           `json:"env_file"`
	Routes  map[string]Route `json:"routes"`
}

// Route represents a single proxy route
type Route struct {
	Target string            `json:"target"`
	Headers map[string]string `json:"headers"`
}

// ProxyRoute extends Route with compiled headers
type ProxyRoute struct {
	Target  string
	Headers map[string]string
}

// ProxyServer holds the server configuration
type ProxyServer struct {
	config  *Config
	routes  map[string]*ProxyRoute
	env     map[string]string
	verbose bool
}
