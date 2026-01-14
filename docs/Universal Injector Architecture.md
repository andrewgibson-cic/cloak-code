# **Architecture Document: Universal API Credential Injector**

## **1\. Executive Architecture Summary**

The Universal API Credential Injector is a middleware infrastructure component designed to decouple authentication logic from application runtime code. It operates as a transparent Man-in-the-Middle (MITM) proxy that intercepts outbound network traffic, identifies service intent via heuristic analysis of "dummy" credentials, and injects high-privilege authentication artifacts (signatures, tokens) before forwarding requests to upstream APIs.

The system is architected to support "Secret-Less" runtimes, specifically targeting AI Agents and ephemeral microservices where credential exfiltration risks are high.

## **2\. High-Level System Design**

### **2.1 Core Components**

The architecture consists of four distinct layers:

1. **The Application Layer (Client):** The source of traffic (e.g., an AI agent, a microservice, or a dev container). It runs with "Dummy Credentials" that satisfy local regex validation but hold no privilege.  
2. **The Network Interception Layer:** Mechanisms to force traffic through the proxy without application awareness (Transparent Mode) or via standard configuration (Explicit Mode).  
3. **The Proxy Core (Logic Engine):** A Python-based mitmproxy instance running custom addon scripts to handle traffic analysis, modification, and cryptographic signing.  
4. **The Secret State Layer:** Secure storage (HashiCorp Vault, AWS Secrets Manager) and ephemeral memory within the proxy where real credentials serve as inputs for signing operations.

### **2.2 Component Diagram (Conceptual)**

graph TD  
    subgraph "Untrusted Zone (Application)"  
        App\[AI Agent / Microservice\]  
        DummyCreds\[Dummy Credentials (Env Vars)\]  
        App \--\>|Uses Dummy Creds| HTTPClient\[HTTP Client SDK\]  
    end

    subgraph "Trust Boundary (Proxy Container)"  
        Kernel\[Linux Kernel / Network Namespace\]  
        IPTables\[iptables / nftables\]  
          
        subgraph "Mitmproxy Engine"  
            Listener\[Proxy Listener :8080\]  
            Addon\[Injection Script (Python)\]  
            CAService\[Certificate Authority\]  
            Signer\[Crypto Signing Module\]  
        end  
          
        Secrets\[In-Memory Real Secrets\]  
    end

    subgraph "External World"  
        AWS\[AWS API (SigV4)\]  
        Stripe\[Stripe API (Bearer)\]  
        Binance\[Binance API (HMAC)\]  
    end

    HTTPClient \--\>|Raw Traffic| Kernel  
    Kernel \--\>|Redirect :80/443 \-\> :8080| IPTables  
    IPTables \--\> Listener  
    Listener \--\>|Decrypted Flow| Addon  
    Addon \--\>|Read| Secrets  
    Addon \--\>|Sign| Signer  
    Signer \--\>|Inject Headers| Listener  
    Listener \--\>|Signed Request| AWS  
    Listener \--\>|Signed Request| Stripe

## **3\. Detailed Component Specifications**

### **3.1 Network Interception Layer**

This layer is responsible for capturing traffic. We support two modes, with **Transparent Mode** being the architectural standard for AI agents.

* **Mechanism:** iptables redirection within a shared network namespace (Docker network\_mode: service:proxy or Kubernetes Pod).  
* **Routing Logic:**  
  * **Ingress:** Traffic from the App container enters the Proxy container's network stack.  
  * **Rule:** iptables \-t nat \-A OUTPUT \-p tcp \-m owner \! \--uid-owner mitmproxy \-m multiport \--dports 80,443 \-j REDIRECT \--to-port 8080  
  * **Exemption:** Traffic originating from the mitmproxy user (UID-based filtering) bypasses the redirection to prevent infinite loops.  
* **Protocol Handling:**  
  * **HTTP/1.1 & HTTP/2:** Fully parsed and modified.  
  * **TCP (Generic):** Tunneled or intercepted via SOCKS5 for non-HTTP protocols (e.g., database traffic), though modification capabilities are limited compared to HTTP.

### **3.2 The Trust Barrier (TLS Termination)**

To inspect HTTPS traffic, the proxy must terminate TLS.

* **Dynamic CA:** The proxy generates a Root CA certificate (mitmproxy-ca-cert.pem) at initialization.  
* **On-the-Fly Signing:** When the App connects to api.stripe.com, the proxy generates a leaf certificate for that domain signed by its Root CA.  
* **Trust Distribution:**  
  * **Bootstrapper:** An init container or script must mount the generated CA into the App container's trust stores.  
  * **Target Stores:**  
    * OS Level: /etc/ssl/certs (Linux), /etc/pki/tls/certs (RHEL).  
    * Language Specific: Python certifi, Java cacerts (JKS), Node.js NODE\_EXTRA\_CA\_CERTS.

### **3.3 The Injection Logic Engine (Python Addon)**

The core logic resides in a mitmproxy addon script class CredentialInjector.

#### **3.3.1 Detection Phase**

* **Input:** Decrypted HTTP request object.  
* **Heuristics:**  
  * **Header Scanning:** Scans Authorization headers for specific "Dummy" patterns (e.g., AKIA00000000DUMMYKEY).  
  * **Host Matching:** Checks Host header against known API endpoints (e.g., \*.amazonaws.com).  
* **Fail-Open Logic:** If no dummy credential is detected, the request is passed through unmodified. This allows developers to use manual keys if necessary.

#### **3.3.2 Sanitization Phase**

* **Objective:** Remove artifacts of the dummy credential to prevent conflicts.  
* **Actions:**  
  * Strip Authorization headers containing dummy values.  
  * Strip X-Amz-Date and X-Amz-Security-Token for AWS requests (as these are tied to the signature).  
  * Strip signature query parameters for HMAC-based APIs (Binance).

#### **3.3.3 Signing & Injection Phase**

The architecture supports modular "Strategies" for different authentication protocols:

* **Strategy A: Bearer Token Replacement (Simple)**  
  * **Target:** Stripe, OpenAI.  
  * **Action:** headers\["Authorization"\] \= "Bearer " \+ vault.get("STRIPE\_LIVE\_KEY")  
* **Strategy B: AWS SigV4 (Complex)**  
  * **Target:** AWS SDKs.  
  * Action: 1\. Reconstruct botocore.awsrequest.AWSPreparedRequest.  
    2\. Load real credentials (AccessKey, SecretKey, SessionToken).  
    3\. Compute SigV4 signature (Canonical Request \-\> String to Sign \-\> Signature).  
    4\. Payload Optimization: For S3, inject x-amz-content-sha256: UNSIGNED-PAYLOAD to avoid buffering large bodies in memory.  
* **Strategy C: Query Param HMAC (Complex)**  
  * **Target:** Binance, Crypto Exchanges.  
  * **Action:**  
    1. Parse query parameters.  
    2. Update timestamp parameter to current proxy time (drift correction).  
    3. Compute HMAC-SHA256(secret, query\_string).  
    4. Append \&signature=... to the URL.

## **4\. Secret Management Architecture**

* **Source of Truth:** Secrets are never stored permanently in the proxy image.  
* **Injection:**  
  * **Production:** Secrets are injected as Environment Variables into the Proxy container via orchestration tools (K8s Secrets, Vault Agent Injector).  
  * **Development:** .env files loaded by Docker Compose, excluded from git.  
* **Memory Hygiene:** The Python runtime manages secrets in memory. While complete memory protection in Python is difficult, the container isolation provides the primary security boundary.

## **5\. Deployment Topologies**

### **5.1 Docker Compose (Sidecar)**

* **Container A (App):** network\_mode: service:proxy.  
* **Container B (Proxy):** privileged: true (for iptables), volume mount for CA certs.

### **5.2 Kubernetes (Pod Sidecar)**

* **Pod:**  
  * **InitContainer:** Sets up iptables rules to redirect traffic to localhost:8080.  
  * **Container A (App):** Runs the workload.  
  * **Container B (Proxy):** Runs mitmproxy, listens on localhost:8080.  
* **Shared Volume:** An emptyDir volume shares the CA certificate between containers.