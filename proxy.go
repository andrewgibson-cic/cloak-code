package main

import (
	"bytes"
	"crypto/tls"
	"encoding/pem"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"

	"github.com/elazarl/goproxy"
)

// StartTransparentProxy starts the transparent MITM proxy
func (ps *ProxyServer) StartTransparentProxy(caCertBytes, caKeyBytes []byte) error {
	proxy := goproxy.NewProxyHttpServer()
	proxy.Verbose = ps.verbose

	// Load CA certificate for MITM
	goproxyCa, err := tls.X509KeyPair(caCertBytes, caKeyBytes)
	if err != nil {
		return fmt.Errorf("failed to load CA key pair: %w", err)
	}

	// Set the custom CA globally for MITM
	goproxy.GoproxyCa = goproxyCa

	// Set up magic domain handler FIRST (before other handlers)
	ps.setupMagicDomainHandler(proxy)

	// Set up domain-based credential injection and MITM
	ps.setupDomainHandlers(proxy)

	return http.ListenAndServe(fmt.Sprintf(":%d", ps.config.Port), proxy)
}

// setupDomainHandlers configures credential injection and MITM for each domain
func (ps *ProxyServer) setupDomainHandlers(proxy *goproxy.ProxyHttpServer) {
	for domain, rule := range ps.config.Domains {
		ps.setupDomainHandler(proxy, domain, rule)
	}
}

// setupDomainHandler configures a single domain's credential injection
func (ps *ProxyServer) setupDomainHandler(proxy *goproxy.ProxyHttpServer, domain string, rule DomainRule) {
	// Enable MITM for this domain (required for HTTPS)
	proxy.OnRequest(goproxy.DstHostIs(domain)).HandleConnect(goproxy.AlwaysMitm)

	// Create a closure to capture the domain and rule for this handler
	handler := func(req *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
		if ps.verbose {
			log.Printf("→ [%s] %s %s", domain, req.Method, req.URL.String())
			log.Printf("  [%s] ReplaceValues: %v, InjectHeaders: %d", domain, rule.ReplaceValues, len(rule.InjectHeaders))
			log.Printf("  [%s] Request Host: %s, URL.Host: %s", domain, req.Host, req.URL.Host)
		}

		// Step 1: Replace placeholder values in existing headers (replace_values)
		if len(rule.ReplaceValues) > 0 {
			ps.replaceHeaderValues(req, domain, rule)
		}

		// Step 2: Inject new headers defined in configuration (inject_headers)
		for headerName, headerValueTemplate := range rule.InjectHeaders {
			// Expand environment variables in the header value
			headerValue := ExpandVariables(headerValueTemplate, ps.env)

			if headerValue == "" && strings.Contains(headerValueTemplate, "${") {
				log.Printf("WARNING: [%s] Header %s: variable expansion FAILED for template '%s'", domain, headerName, headerValueTemplate)
			}

			req.Header.Set(headerName, headerValue)

			if ps.verbose {
				// Mask sensitive headers in logs
				displayValue := headerValue
				if isSensitiveHeader(headerName) && len(headerValue) > 8 {
					displayValue = "***" + headerValue[len(headerValue)-4:]
				}
				log.Printf("  [%s] Injected: %s: %s", domain, headerName, displayValue)
			}
		}

		return req, nil
	}

	// Register handler for this domain
	// Use ReqHostMatches with regex for domain matching
	proxy.OnRequest(goproxy.ReqHostMatches(regexp.MustCompile("^"+regexp.QuoteMeta(domain)+"$"))).DoFunc(handler)

	if ps.verbose {
		log.Printf("✓ Registered MITM and handler for domain: %s", domain)
	}
}

// setupMagicDomainHandler sets up the special mitm.it domain for CA certificate distribution
func (ps *ProxyServer) setupMagicDomainHandler(proxy *goproxy.ProxyHttpServer) {
	// Handle requests to mitm.it - serve the CA certificate
	proxy.OnRequest(goproxy.DstHostIs("mitm.it")).DoFunc(
		func(req *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
			// Parse the path to determine format
			path := req.URL.Path

			var certPEM []byte
			var contentType string
			var filename string

			switch {
			case strings.HasSuffix(path, "/pem"):
				certPEM = ps.getCaCertPEM()
				contentType = "application/x-pem-file"
				filename = "env-sidecar-ca.crt"
			case strings.HasSuffix(path, "/crt"):
				certPEM = ps.getCaCertPEM()
				contentType = "application/x-x509-ca-cert"
				filename = "env-sidecar-ca.crt"
			case strings.HasSuffix(path, "/p12"):
				// p12 format not supported, return error
				return req, goproxy.NewResponse(
					req,
					goproxy.ContentTypeText,
					http.StatusNotImplemented,
					"P12 format not supported. Please use PEM format.",
				)
			default:
				// Root path - return HTML with download links
				html := `<!DOCTYPE html>
<html>
<head>
	<title>env-sidecar CA Certificate</title>
	<style>
		body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
		h1 { color: #333; }
		.info { background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }
		.button { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
		.button:hover { background: #0056b3; }
	</style>
</head>
<body>
	<h1>env-sidecar CA Certificate</h1>
	<div class="info">
		<p><strong>env-sidecar</strong> is running as a transparent HTTPS proxy.</p>
		<p>To use HTTPS services, you need to trust this CA certificate.</p>
	</div>
	<h2>Download Certificate</h2>
	<p>Select your preferred format:</p>
	<p>
		<a href="/cert/pem" class="button">Download PEM (Recommended)</a>
		<a href="/cert/crt" class="button">Download CRT</a>
	</p>
	<h2>Installation Instructions</h2>
	<h3>Linux/Devcontainer:</h3>
	<pre><code># Download and install
curl -s http://mitm.it/cert/pem -o /tmp/env-sidecar-ca.crt
sudo cp /tmp/env-sidecar-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates</code></pre>
	<h3>macOS:</h3>
	<pre><code># Download and add to keychain
curl -s http://mitm.it/cert/pem -o env-sidecar-ca.crt
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain env-sidecar-ca.crt</code></pre>
</body>
</html>`
				return req, goproxy.NewResponse(
					req,
					"text/html",
					http.StatusOK,
					html,
				)
			}

			// Return the certificate
			resp := goproxy.NewResponse(req, contentType, http.StatusOK, string(certPEM))
			resp.Header.Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))
			return req, resp
		},
	)

	if ps.verbose {
		log.Printf("✓ Registered magic domain handler: mitm.it")
	}
}

// getCaCertPEM returns the CA certificate in PEM format
func (ps *ProxyServer) getCaCertPEM() []byte {
	certPath := ps.config.CA.CertPath
	certBytes, err := ps.readCertFile(certPath)
	if err != nil {
		log.Printf("ERROR: Failed to read CA certificate: %v", err)
		return []byte("Error loading CA certificate")
	}
	return certBytes
}

// readCertFile reads a certificate file and returns PEM-encoded bytes
func (ps *ProxyServer) readCertFile(path string) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	// If it's already in PEM format, return as-is
	if bytes.Contains(data, []byte("-----BEGIN")) {
		return data, nil
	}

	// Otherwise, convert to PEM
	block := &pem.Block{
		Type:  "CERTIFICATE",
		Bytes: data,
	}
	return pem.EncodeToMemory(block), nil
}

// isSensitiveHeader returns true if the header contains sensitive data
func isSensitiveHeader(name string) bool {
	sensitiveHeaders := []string{"authorization", "x-api-key", "cookie", "set-cookie"}
	lowerName := strings.ToLower(name)
	for _, h := range sensitiveHeaders {
		if strings.EqualFold(name, h) || strings.Contains(lowerName, h) {
			return true
		}
	}
	return false
}

// replaceHeaderValues scans headers and replaces placeholder values with real values
// e.g., "Authorization: Bearer API_KEY" becomes "Authorization: Bearer sk-..."
func (ps *ProxyServer) replaceHeaderValues(req *http.Request, domain string, rule DomainRule) {
	log.Printf("  [%s] replaceHeaderValues called with placeholders: %v", domain, rule.ReplaceValues)

	// Build a set of headers to scan (or all headers if not restricted)
	headersToScan := make(map[string]bool)
	if len(rule.ReplaceInHeaders) > 0 {
		// Only scan specified headers
		for _, h := range rule.ReplaceInHeaders {
			headersToScan[strings.ToLower(h)] = true
		}
	}

	// For each header in the request
	for headerName, headerValues := range req.Header {
		// Skip if we have a restricted list and this header isn't in it
		if len(headersToScan) > 0 && !headersToScan[strings.ToLower(headerName)] {
			continue
		}

		// Process each value for this header (though most headers have single values)
		for i, originalValue := range headerValues {
			newValue := originalValue

			// Replace each placeholder in the value
			for _, placeholder := range rule.ReplaceValues {
				// Check if the placeholder exists as a value in our env
				realValue, exists := ps.env[placeholder]
				if !exists {
					log.Printf("  [%s] WARNING: Placeholder '%s' not found in env", domain, placeholder)
					continue
				}

				log.Printf("  [%s] Checking %s: %s for placeholder %s", domain, headerName, originalValue, placeholder)

				// Replace exact matches (e.g., "API_KEY" -> "sk-...")
				if newValue == placeholder {
					newValue = realValue
				} else if strings.Contains(newValue, placeholder) {
					// Also replace if placeholder appears anywhere in the value
					// e.g., "Bearer API_KEY" -> "Bearer sk-..."
					newValue = strings.ReplaceAll(newValue, placeholder, realValue)
				}
			}

			// Only update if something changed
			if newValue != originalValue {
				headerValues[i] = newValue
				if ps.verbose {
					displayValue := newValue
					if isSensitiveHeader(headerName) && len(newValue) > 8 {
						displayValue = "***" + newValue[len(newValue)-4:]
					}
					log.Printf("  [%s] Replaced in %s: %s", domain, headerName, displayValue)
				}
			}
		}
	}
}
