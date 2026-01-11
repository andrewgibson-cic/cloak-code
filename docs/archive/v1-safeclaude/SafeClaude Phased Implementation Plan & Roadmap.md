# **Phased Implementation Plan & Roadmap**

This document outlines the step-by-step execution plan for building the Secure "Zero-Knowledge" Agent Environment. It is designed to be followed sequentially.

## **Phase 1: Infrastructure Initialization & Setup**

**Goal:** Create the folder structure, secure credentials, and define the container environment.

### **Step 1.1: Create Project Directory Structure**

* **Description:** You need a clean workspace on your computer to hold the configuration files for this secure environment.  
* **Human Action (Terminal):** Open your terminal or command prompt and run the following commands exactly:  
  mkdir \-p claude-secure-env/certs  
  mkdir \-p claude-secure-env/proxy  
  mkdir \-p claude-secure-env/agent  
  cd claude-secure-env

* **Result:** You now have a main folder claude-secure-env with three empty subfolders inside it.

### **Step 1.2: Secret Provisioning (The .env File)**

* **Description:** This file will hold the *Real* API keys. It acts as the "vault." The Proxy container will read this, but the Agent container will never see it.  
* **Human Action (Manual):**  
  1. Sign up for the services you need (e.g., OpenAI, GitHub, AWS) and get your API Keys.  
  2. Create a file named .env inside the claude-secure-env folder.  
  3. Paste your keys into the file using this format:  
     \# .env file  
     REAL\_OPENAI\_API\_KEY=sk-proj-123456...  
     REAL\_GITHUB\_TOKEN=ghp\_abcdef...

  4. **Critical Security Step:** Create a file named .gitignore in the same folder and write .env inside it. This prevents you from accidentally uploading your secrets to the internet.

### **Step 1.3: Create the Proxy Script (inject.py)**

* **Description:** This Python script tells the proxy server how to swap the "Dummy" keys for "Real" keys.  
* **Human Action (Code Creation):** Create a file at claude-secure-env/proxy/inject.py and paste the logic that:  
  1. Intercepts HTTP requests.  
  2. Checks if the header contains DUMMY\_OPENAI\_KEY.  
  3. If yes, replaces it with os.environ\["REAL\_OPENAI\_API\_KEY"\].  
  4. *Crucially*, checks if the request URL is api.openai.com. If it's not (e.g., evil-hacker.com), it drops the request.

### **Step 1.4: Define the Agent Dockerfile (Dockerfile)**

* **Description:** This file is the "recipe" for the Agent's computer. It tells Docker what operating system and software to install.  
* **Human Action (Code Creation):** Create a file at claude-secure-env/agent/Dockerfile.  
* **Key Contents to Include:**  
  * FROM node:20-bookworm (This uses a stable, compatible version of Linux).  
  * RUN npm install \-g @anthropic-ai/claude-code (Installs the AI agent).  
  * RUN useradd \-m \-u 1000 claude (Creates a safe user account so the agent doesn't run as Root/Administrator).

### **Step 1.5: Orchestrate with Docker Compose (docker-compose.yml)**

* **Description:** This file connects the two containers (Agent and Proxy) and sets up the networking.  
* **Human Action (Code Creation):** Create claude-secure-env/docker-compose.yml.  
* **Key Configurations:**  
  * **Service 1 (Proxy):** Mount the .env file here. Expose port 8080\.  
  * **Service 2 (Agent):** DO NOT mount .env here. Set environment variables HTTP\_PROXY=http://proxy:8080.  
  * **Volumes:** Define a volume claude\_auth\_data to save the agent's login state.

## **Phase 2: Trust Bootstrapping & First Run**

**Goal:** Turn on the system and ensure the Agent trusts the Proxy.

### **Step 2.1: Start the Environment**

* **Description:** Boot up the containers for the first time.  
* **Human Action (Terminal):** Run:  
  docker-compose up \-d

* **What Happens:** Docker downloads the images and starts the containers in the background (-d).

### **Step 2.2: Certificate Trust Installation (Automatic)**

* **Description:** The Proxy creates a special security certificate ("ID card") so it can read encrypted traffic. The Agent needs to trust this ID card.  
* **System Action (Automatic via Entrypoint):**  
  1. The Proxy generates mitmproxy-ca-cert.pem and places it in the shared /certs folder.  
  2. The Agent starts up, sees the file in /certs, and runs update-ca-certificates.  
* **Verification:** To check if this worked, run docker logs claude\_agent. You should see a message like "Certificate installed successfully."

## **Phase 3: Authentication (The "Headless" Login)**

**Goal:** Log the Agent into Anthropic so it can use the Claude 3.7 Sonnet model. You only need to do this *once*.

### **Step 3.1: Trigger the Login**

* **Description:** You need to tell the Agent to start the login process.  
* **Human Action (Terminal):** Run:  
  docker exec \-it claude\_agent claude login

  * docker exec: Run a command inside a container.  
  * \-it: Interactive mode (lets you type).  
  * claude\_agent: The name of the container.  
  * claude login: The command to run.

### **Step 3.2: Complete Login in Browser**

* **Description:** The Agent cannot open a browser window because it is inside a container. It will print a URL instead.  
* **Human Action:**  
  1. Look at the terminal output. It will show a long link starting with https://....  
  2. Copy that link.  
  3. Open Chrome/Safari/Edge on your *real* computer.  
  4. Paste the link and hit Enter.  
  5. Log in to your Anthropic account and click "Allow."  
* **Result:** The browser will say "Success," and the terminal will show that the login is complete.

### **Step 3.3: Verify Persistence**

* **Description:** Ensure that if we restart the computer, we don't have to log in again.  
* **Human Action:**  
  1. Run docker restart claude\_agent.  
  2. Run docker exec \-it claude\_agent claude whoami.  
* **Success Criteria:** It should print your username/email, proving it remembered the login.

## **Phase 4: The Daily Workflow (Steady State)**

**Goal:** How to actually use this tool to write code.

### **Step 4.1: Enter the Sandbox**

* **Description:** Step inside the container to start working.  
* **Human Action (Terminal):**  
  docker exec \-it claude\_agent bash

* **Result:** Your terminal prompt will change (e.g., claude@container-id:\~$). You are now "inside" the matrix.

### **Step 4.2: Navigate to Code**

* **Human Action:**  
  cd workspace

* **Note:** This folder is connected to your real project folder on your host machine. Any file you change here changes on your real computer too.

### **Step 4.3: Operate the Agent**

* **Description:** Give the Agent instructions.  
* **Human Action:**  
  claude "Analyze the src/ folder and write a README.md file explaining the architecture."

* **What Happens:**  
  1. Claude reads the files.  
  2. Claude thinks.  
  3. Claude writes the README.md.  
  4. You see the file appear in your VS Code / Editor on your host machine immediately.

## **Phase 5: Recovery Protocols (Emergency Procedures)**

**Goal:** What to do when things go wrong.

### **Step 5.1: The Agent is "Stuck" or "Hallucinating"**

* **Scenario:** The Agent is running a command that won't stop, or it has edited a system file it shouldn't have.  
* **Action:**  
  docker restart claude\_agent

* **Result:** The computer reboots in 2 seconds. The operating system is reset to the clean original state. Your code (in workspace) and your login (in auth volume) are safe.

### **Step 5.2: The "Nuke and Pave" (Total Reset)**

* **Scenario:** You suspect the environment is corrupted or you want a fresh start.  
* **Action:**  
  docker-compose down  
  docker-compose up \-d

* **Result:** Deletes the computers entirely and builds brand new ones from scratch.