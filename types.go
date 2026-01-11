package main

// Config represents the sidecar configuration
type Config struct {
	Port    int                    `json:"port"`
	EnvFile string                 `json:"env_file"`
	Domains map[string]DomainRule  `json:"domains"`
	CA      CAConfig               `json:"ca"`
}

// DomainRule represents credential injection rules for a specific domain
type DomainRule struct {
	// InjectHeaders sets specific headers with variable expansion
	InjectHeaders map[string]string `json:"inject_headers"`

	// ReplaceValues scans all headers and replaces placeholder values with real values
	// e.g., if the client sends "Authorization: Bearer API_KEY", it becomes "Authorization: Bearer sk-..."
	ReplaceValues []string `json:"replace_values"`

	// ReplaceInHeaders restricts which headers are scanned for replacements (optional)
	// If empty, all headers are scanned. Useful for security.
	ReplaceInHeaders []string `json:"replace_in_headers"`
}

// CAConfig represents CA certificate configuration
type CAConfig struct {
	CertPath  string `json:"cert_path"`
	CAKeyPath string `json:"key_path"`
}

// ProxyServer holds the server configuration
type ProxyServer struct {
	config  *Config
	env     map[string]string
	verbose bool
}
