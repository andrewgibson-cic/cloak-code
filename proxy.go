package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
)

// removeHopByHopHeaders removes headers that should not be proxied
func removeHopByHopHeaders(h http.Header) {
	hopByHopHeaders := []string{
		"Connection",
		"Keep-Alive",
		"Proxy-Authenticate",
		"Proxy-Authorization",
		"Te",
		"Trailers",
		"Transfer-Encoding",
		"Upgrade",
		// Remove proxy forwarding headers that might cause issues with upstream APIs
		"X-Forwarded-For",
		"X-Forwarded-Host",
		"X-Forwarded-Proto",
	}

	for _, header := range hopByHopHeaders {
		h.Del(header)
	}
}

// handleRequest handles incoming HTTP requests and forwards them to the appropriate target
func (ps *ProxyServer) handleRequest(w http.ResponseWriter, r *http.Request) {
	if ps.verbose {
		log.Printf("Incoming request: %s %s", r.Method, r.URL.Path)
	}

	// Get the matching route
	route, exists := ps.findRoute(r.URL.Path)
	if !exists {
		if ps.verbose {
			log.Printf("No route found for path: %s", r.URL.Path)
		}
		http.Error(w, "No route configured for this path", http.StatusNotFound)
		return
	}

	if ps.verbose {
		log.Printf("Route matched: %s -> %s", r.URL.Path, route.Target)
	}

	// Parse the target URL
	targetURL, err := url.Parse(route.Target)
	if err != nil {
		log.Printf("Invalid target URL: %v", err)
		http.Error(w, "Invalid target URL", http.StatusBadGateway)
		return
	}

	// Create reverse proxy director
	director := func(req *http.Request) {
		// Set the target URL scheme and host
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host

		// Explicitly set the Host header to match the target
		req.Host = targetURL.Host

		// Remove the route prefix from the path
		// For example, if route is /openai and request is /openai/chat/completions
		// we want to forward to targetURL/chat/completions
		originalPath := req.URL.Path
		req.RequestURI = ""
		req.URL.Path = strings.TrimPrefix(req.URL.Path, ps.findMatchingRoutePrefix(req.URL.Path))

		// Prepend the target URL's path to the request path
		if targetURL.Path != "" {
			req.URL.Path = targetURL.Path + req.URL.Path
		}

		if ps.verbose {
			log.Printf("Proxying: %s -> %s%s", originalPath, targetURL.String(), req.URL.Path)
		}

		// Replace header values that match replace_values entries
		// This scans ALL headers and replaces any occurrence of an env var name
		// with the real value from .env.vault
		replacedAuthHeaders := make(map[string]bool)
		for headerName, headerValues := range req.Header {
			for i, headerValue := range headerValues {
				newValue := headerValue
				// Check if this header value contains any of our replace_values keys
				for envVarName, realValue := range route.ReplaceValues {
					if strings.Contains(headerValue, envVarName) {
						newValue = strings.ReplaceAll(headerValue, envVarName, realValue)
						replacedAuthHeaders[headerName] = true
						if ps.verbose {
							log.Printf("Replaced in header %s: %s -> ***", headerName, envVarName)
						}
					}
				}
				if newValue != headerValue {
					req.Header[headerName][i] = newValue
				}
			}
		}

		// Remove Authorization and X-Api-Key headers that were NOT replaced
		// (This preserves headers that were successfully replaced via replace_values)
		if !replacedAuthHeaders["Authorization"] {
			req.Header.Del("Authorization")
		}
		if !replacedAuthHeaders["X-Api-Key"] {
			req.Header.Del("X-Api-Key")
		}

		// Add secure headers from configuration
		for key, value := range route.Headers {
			req.Header.Set(key, value)
			if ps.verbose && len(value) == 0 {
				log.Printf("WARNING: Injecting empty header: %s", key)
			}
		}

		// Auto-inject common API headers for known services
		// Anthropic API requires anthropic-version header
		if targetURL.Host == "api.anthropic.com" {
			if req.Header.Get("anthropic-version") == "" {
				req.Header.Set("anthropic-version", "2023-06-01")
			}
		}

		// Remove hop-by-hop headers
		removeHopByHopHeaders(req.Header)
	}

	// Create and configure the reverse proxy
	proxy := &httputil.ReverseProxy{
		Director: director,
	}

	// Add custom transport to remove proxy headers that ReverseProxy adds automatically
	if ps.verbose {
		proxy.Transport = &verboseTransport{
			transport: http.DefaultTransport,
		}
	} else {
		proxy.Transport = &productionTransport{
			transport: http.DefaultTransport,
		}
	}

	// Add error handler
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("Proxy error: %v", err)
		http.Error(w, fmt.Sprintf("Proxy error: %v", err), http.StatusBadGateway)
	}

	// Serve the request
	proxy.ServeHTTP(w, r)
}

// productionTransport removes proxy headers without logging
type productionTransport struct {
	transport http.RoundTripper
}

func (pt *productionTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// Remove proxy headers that ReverseProxy adds automatically
	req.Header.Del("X-Forwarded-For")
	req.Header.Del("X-Forwarded-Host")
	req.Header.Del("X-Forwarded-Proto")
	return pt.transport.RoundTrip(req)
}

// verboseTransport removes proxy headers and logs details
type verboseTransport struct {
	transport http.RoundTripper
}

func (vt *verboseTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// Remove proxy headers that ReverseProxy adds automatically
	req.Header.Del("X-Forwarded-For")
	req.Header.Del("X-Forwarded-Host")
	req.Header.Del("X-Forwarded-Proto")

	log.Printf("Actual HTTP Request: %s %s", req.Method, req.URL.String())

	// Log headers (with masked Authorization)
	for key, values := range req.Header {
		for _, value := range values {
			if key == "Authorization" && len(value) > 4 {
				maskedValue := "***" + value[len(value)-4:]
				log.Printf("  %s: %s", key, maskedValue)
			} else {
				log.Printf("  %s: %s", key, value)
			}
		}
	}

	resp, err := vt.transport.RoundTrip(req)
	if err == nil {
		log.Printf("Response status: %d %s", resp.StatusCode, resp.Status)
	}
	return resp, err
}

// findRoute finds the best matching route for a given path
func (ps *ProxyServer) findRoute(path string) (*ProxyRoute, bool) {
	// Direct match first
	if route, exists := ps.routes[path]; exists {
		return route, true
	}

	// Find longest prefix match
	var longestMatch string
	var longestRoute *ProxyRoute

	for routePath, route := range ps.routes {
		if strings.HasPrefix(path, routePath) {
			if len(routePath) > len(longestMatch) {
				longestMatch = routePath
				longestRoute = route
			}
		}
	}

	if longestRoute != nil {
		return longestRoute, true
	}

	return nil, false
}

// findMatchingRoutePrefix finds the matching route prefix for a given path
func (ps *ProxyServer) findMatchingRoutePrefix(path string) string {
	// Direct match first
	if _, exists := ps.routes[path]; exists {
		return path
	}

	// Find longest prefix match
	var longestMatch string

	for routePath := range ps.routes {
		if strings.HasPrefix(path, routePath) {
			if len(routePath) > len(longestMatch) {
				longestMatch = routePath
			}
		}
	}

	return longestMatch
}
