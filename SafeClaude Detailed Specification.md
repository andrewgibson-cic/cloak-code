# **Comprehensive System Specification Document**

## **1\. System Overview**

System Name: Secure Claude Code Development Container (SCCDC)  
Purpose: To provide a sandboxed, recoverable, and credential-safe environment for autonomous AI development agents.

## **2\. Hardware & Host Requirements**

* **REQ-HOST-01**: Host machine must support Docker Engine 24.0+ and Docker Compose v2.0+.  
* **REQ-HOST-02**: Minimum 8GB RAM recommended (Agent runtime \+ Docker overhead).  
* **REQ-HOST-03**: Internet connection required for initial image pull and API communication.

## **3\. Container Specifications**

### **3.1 Agent Container**

* **REQ-AGENT-OS**: Base image MUST be node:20-bookworm or python:3.11-bookworm to ensure glibc compatibility. Alpine Linux is expressly FORBIDDEN due to musl libc incompatibility with common AI/Data Science wheels.  
* **REQ-AGENT-USER**: MUST run as a non-root user named claude.  
* **REQ-AGENT-UID**: User UID MUST be 1000 to align with standard Linux host permissions.  
* **REQ-AGENT-SUDO**: User claude MUST have passwordless sudo access enabled to facilitate autonomous package installation.  
* **REQ-AGENT-TOOLS**: Image MUST include: git, curl, jq, vim/nano, python3, pip, build-essential, ca-certificates.  
* **REQ-AGENT-CLI**: MUST install @anthropic-ai/claude-code globally via npm.  
* **REQ-AGENT-ENV**: MUST define the following environment variables:  
  * HTTP\_PROXY \= http://proxy:8080  
  * HTTPS\_PROXY \= http://proxy:8080  
  * NO\_PROXY \= localhost,127.0.0.1  
  * NODE\_EXTRA\_CA\_CERTS \= /usr/local/share/ca-certificates/mitmproxy.crt (Node.js specific)  
  * REQUESTS\_CA\_BUNDLE \= /etc/ssl/certs/ca-certificates.crt (Python specific)  
  * OPENAI\_API\_KEY \= DUMMY\_OPENAI\_KEY (and similar for other services)

### **3.2 Proxy Container**

* **REQ-PROXY-IMG**: Base image MUST be mitmproxy/mitmproxy:10.0.0 or later.  
* **REQ-PROXY-PORT**: MUST listen on port 8080 (Standard proxy port) bound to 0.0.0.0.  
* **REQ-PROXY-SCRIPT**: MUST load a Python script via the \-s flag (mitmdump \-s /scripts/inject.py).  
* **REQ-PROXY-SSL**: MUST run with \--set ssl\_insecure=true (to allow upstream connections without strict validation if needed, though production should verify upstream).  
* **REQ-PROXY-VOL**: MUST mount the .env file containing real credentials. This file MUST NOT be mounted to the Agent.

## **4\. Volume & Storage Requirements**

* **REQ-VOL-AUTH**: A Docker Named Volume (claude\_auth\_data) MUST be mounted to /home/claude/.config/claude-code to persist authentication tokens.  
* **REQ-VOL-CERTS**: A bind mount or named volume MUST be shared between Proxy (Read/Write) and Agent (Read-Only) at /certs.  
* **REQ-VOL-CODE**: The host project directory MUST be bind-mounted to /home/claude/workspace.

## **5\. Functional Requirements**

### **5.1 Initialization Logic (entrypoint.sh)**

* **REQ-FUNC-INIT-01**: Agent script MUST wait for the existence of /certs/mitmproxy-ca-cert.pem.  
* **REQ-FUNC-INIT-02**: Script MUST timeout after 30 seconds if cert is not found.  
* **REQ-FUNC-INIT-03**: Script MUST copy the cert to /usr/local/share/ca-certificates/ and run update-ca-certificates.

### **5.2 Credential Injection Logic (inject.py)**

* **REQ-FUNC-INJ-01**: Script MUST intercept every HTTP request.  
* **REQ-FUNC-INJ-02**: Script MUST check the Authorization header for presence of predefined DUMMY strings.  
* **REQ-FUNC-INJ-03**: Script MUST validate the destination Host against a hardcoded whitelist for that specific token type (e.g., DUMMY\_GITHUB \-\> api.github.com).  
* **REQ-FUNC-INJ-04**: If validation passes, Script MUST replace the DUMMY string with the REAL value from environment variables.  
* **REQ-FUNC-INJ-05**: Script MUST NOT log the REAL value to any output (console or file). It MAY log that an "Injection Occurred" for audit purposes.

## **6\. Security Requirements**

* **REQ-SEC-GITIGNORE**: The .env file containing real secrets MUST be included in .gitignore.  
* **REQ-SEC-NET**: Containers MUST communicate on an internal Docker network (internal\_net) that is not exposed to the public internet, except via the Proxy's gateway.  
* **REQ-SEC-BLOCK**: The Proxy MUST respond with 418 or 403 to any request destined for known telemetry endpoints defined in a blocklist.