# **Architecture Design Document: Secure "Zero-Knowledge" Agent Environment**

## **1\. Executive Summary**

This document details the architecture for a secure, isolated runtime environment designed for the Claude Code CLI agent. The core architectural philosophy is "Zero-Knowledge Operations," meaning the AI agent is granted the authority to request actions but is never given the cryptographic means (credentials) to authenticate those actions.

## **2\. High-Level Architecture**

The system utilizes a **Containerized Sidecar Proxy Pattern** orchestrated via Docker Compose. This topology strictly decouples the **Execution Environment** (the Agent) from the **Authentication Layer** (the Proxy).

### **2.1 Core Components**

1. **The Agent Container (claude\_agent)**:  
   * **Role**: The "Hands-on-Keyboard" operator. It runs the Claude Code CLI, executes terminal commands, and manipulates the project codebase.  
   * **State**: Ephemeral. Designed to be destroyed and recreated instantly to recover from hallucinations or system breakage.  
   * **Security Context**: Untrusted. It holds *no* real secrets, only placeholder "Dummy Tokens."  
   * **Base Image**: node:20-bookworm (Debian Bookworm ensures glibc compatibility for broad tool support).  
2. **The Proxy Container (secure\_proxy)**:  
   * **Role**: The "Keyring" and Network Gateway. It intercepts all outgoing traffic from the agent.  
   * **State**: Persistent configuration, ephemeral runtime.  
   * **Security Context**: Trusted High-Security Zone. This is the *only* component that has access to the .env file containing real API keys.  
   * **Software**: mitmproxy running a custom Python injection script.

## **3\. Detailed Component Architecture**

### **3.1 Network Traffic Flow (The Interception Model)**

The architecture relies on a Man-in-the-Middle (MITM) attack simulation to inject credentials on the fly.

1. **Request Initiation**: The Agent initiates an HTTP request (e.g., to api.github.com) using a DUMMY\_TOKEN.  
2. **Routing**: The Agent's environment variables (HTTP\_PROXY, HTTPS\_PROXY) force all traffic to the secure\_proxy container on port 8080\.  
3. **Interception**: mitmproxy pauses the request before it leaves the internal network.  
4. **Inspection & Injection**:  
   * The custom Python script inspects the headers.  
   * It identifies the DUMMY\_TOKEN.  
   * It validates the destination host against a **Strict Whitelist** (e.g., ensuring OpenAI keys only go to api.openai.com).  
   * It retrieves the REAL\_TOKEN from the Proxy's secure environment variables.  
   * It swaps the token in the HTTP Header.  
5. **Egress**: The modified request (now authenticated) is sent to the external provider.  
6. **Response**: The provider responds to the Proxy, which forwards the data back to the Agent.

### **3.2 Volume & Persistence Strategy**

To balance "Recoverability" with "Usability," a **Split-State Volume Strategy** is employed.

* **Root Filesystem (/)**: **Ephemeral (Read-Only/Copy-on-Write)**.  
  * Any system-level changes (e.g., apt-get install, rm \-rf /usr) are lost upon container restart. This guarantees recovery from destructive agent hallucinations.  
* **Authentication State (\~/.config/claude-code)**: **Persistent (Docker Volume)**.  
  * A named Docker volume (claude\_auth\_data) mounts to the agent's config directory.  
  * **Purpose**: Stores the OAuth refresh tokens generated during the initial claude login. This ensures the user does not have to re-authenticate with Anthropic every time the container is reset.  
* **Project Workspace (/home/claude/workspace)**: **Bind Mount**.  
  * Maps the local host directory containing source code into the container.  
  * **Purpose**: Allows the agent to modify code that is immediately visible to the developer's host IDE.  
* **Certificates (/certs)**: **Shared Volume**.  
  * Shared between Proxy and Agent.  
  * **Purpose**: The Proxy generates a unique CA certificate on startup; the Agent mounts this to trust the Proxy's interception.

### **3.3 Security Boundaries & User Privileges**

* **Host Isolation**: The Agent runs in a Docker container, isolated from the host OS (macOS/Windows/Linux). It cannot access personal files (\~/Documents, \~/.ssh) unless explicitly mounted.  
* **User ID Mapping**: The Agent runs as a non-root user (claude, UID 1000\) to match standard host user permissions, preventing file ownership issues on the bind-mounted workspace.  
* **Sudo Access**: The claude user is granted passwordless sudo *inside the container*.  
  * *Justification*: The agent often needs to install dependencies. Since the container is ephemeral, "breaking" the container with bad sudo commands is an acceptable risk (resolved by restart).

## **4\. Technology Stack**

* **Orchestration**: Docker Compose (v3.8+)  
* **Proxy Logic**: Python 3.11 (Mitmproxy Scripting API)  
* **Agent Runtime**: Node.js 20 (Required for Claude Code)  
* **OS**: Debian 12 (Bookworm)  
* **Scripting**: Bash (Entrypoint bootstrapping)