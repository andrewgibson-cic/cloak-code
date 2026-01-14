# **Specification Document: Universal API Credential Injector**

## **1\. Functional Requirements**

### **1.1 Traffic Interception**

* **REQ-INT-001:** The system MUST be capable of intercepting all outbound TCP traffic from the target application container on ports 80 (HTTP) and 443 (HTTPS).  
* **REQ-INT-002:** The system MUST support **Transparent Mode**, requiring no configuration changes to the application code (no HTTP\_PROXY env vars required).  
* **REQ-INT-003:** The system MUST support **Explicit Mode**, respecting standard HTTP\_PROXY, HTTPS\_PROXY, and NO\_PROXY environment variables.  
* **REQ-INT-004:** The system MUST utilize iptables REDIRECT targets to route traffic from the application namespace to the proxy process.

### **1.2 Traffic Analysis & Identification**

* **REQ-ANA-001:** The system MUST parse HTTP/1.1 and HTTP/2 request headers.  
* **REQ-ANA-002:** The system MUST detect "Dummy Credentials" using configurable Regular Expressions (Regex).  
* **REQ-ANA-003:** The system MUST default to "Passthrough Mode" if no Dummy Credentials are detected, forwarding the request "as-is".  
* **REQ-ANA-004:** The system MUST identify the target service provider (AWS, Stripe, Binance) based on Host header and Dummy Credential patterns.

### **1.3 Credential Injection Strategies**

* **REQ-INJ-001 (Bearer):** The system MUST be able to replace the value of the Authorization header with a static secret retrieved from the vault.  
* **REQ-INJ-002 (AWS SigV4):** The system MUST implement the AWS Signature Version 4 protocol.  
  * MUST extract AWS Region and Service from the URL.  
  * MUST support x-amz-content-sha256: UNSIGNED-PAYLOAD for S3 requests.  
  * MUST re-sign headers including host, x-amz-date, and content-type.  
* **REQ-INJ-003 (HMAC):** The system MUST support generic HMAC-SHA256 signing.  
  * MUST be able to remove specific query parameters (e.g., signature).  
  * MUST be able to update specific query parameters (e.g., timestamp) to the current server time.  
  * MUST calculate HMAC signature and append it to the query string or body.

### **1.4 Secret Management**

* **REQ-SEC-001:** The system MUST accept real credentials via Environment Variables.  
* **REQ-SEC-002:** The system MUST NOT persist real credentials to disk.  
* **REQ-SEC-003:** The system MUST support mapping multiple sets of credentials (e.g., AWS\_PROD, AWS\_DEV) triggered by different Dummy Credential patterns.

### **1.5 Certificate Management**

* **REQ-CRT-001:** The system MUST generate a self-signed Root CA certificate upon startup.  
* **REQ-CRT-002:** The system MUST generate leaf certificates for intercepted domains on-the-fly signed by this Root CA.  
* **REQ-CRT-003:** The system MUST provide a mechanism (volume mount) to share the Root CA public key with the client container.

## **2\. Interface Requirements**

### **2.1 Configuration Schema (config.yaml)**

The system MUST support a YAML configuration file with the following structure:

strategies:  
  \- name: \<string\>  
    type: \<aws\_sigv4 | bearer | hmac\>  
    credentials:  
      access\_key\_env: \<string\>  
      secret\_key\_env: \<string\>

rules:  
  \- domain\_regex: \<string\>  
    trigger\_header\_regex: \<string\>  
    strategy: \<string\>

### **2.2 Logging Interface**

* **REQ-LOG-001:** The system MUST output logs to stdout in JSON format.  
* **REQ-LOG-002:** The system MUST redact sensitive values (Real Credentials, Signatures) from all logs.  
* **REQ-LOG-003:** The system MUST log the decision path (e.g., "Matched Rule: AWS-Prod \-\> Injecting Credentials").

## **3\. Non-Functional Requirements**

### **3.1 Performance**

* **REQ-PERF-001:** The proxy MUST add no more than 50ms of latency to request processing (excluding upstream network time) for non-signing requests.  
* **REQ-PERF-002:** The proxy MUST add no more than 100ms of latency for requests requiring cryptographic signing (AWS SigV4).

### **3.2 Compatibility**

* **REQ-COMP-001:** The system MUST operate within a standard Docker environment (Linux Kernel 5.x+).  
* **REQ-COMP-002:** The Python addon code MUST be compatible with mitmproxy v10.0+.

### **3.3 Reliability**

* **REQ-REL-001:** The system MUST fail open (allow connection without injection) if the injection logic crashes, OR fail closed (drop connection) based on user configuration. Default MUST be fail closed for security.