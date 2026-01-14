# **Phased Plan and Roadmap: Universal API Credential Injector**

## **Phase 1: Local Prototype & Explicit Proxying**

**Goal:** Build the logic engine on your local machine first. We will not use Docker yet. We will verify that we can intercept a request and swap a header.

* **Step 1.1: Local Environment Setup**  
  * **Action:** Open your terminal and verify you have Python 3.10+ installed: python3 \--version.  
  * **Action:** Create a project folder: mkdir universal-injector && cd universal-injector.  
  * **Action:** Create a virtual environment to keep dependencies clean: python3 \-m venv venv.  
  * **Action:** Activate the environment: source venv/bin/activate (Mac/Linux) or venv\\Scripts\\activate (Windows).  
  * **Action:** Install the core proxy tool and AWS library: pip install mitmproxy boto3 requests.  
* **Step 1.2: Dummy Credential Definition**  
  * **Concept:** We need a fake key that looks real enough to pass basic validation checks (like regex) in SDKs but is obviously fake to us.  
  * **Action:** Define these patterns in a text file or just write them down:  
    * **AWS:** AKIA00000000DUMMYKEY (The AKIA prefix is required by AWS SDKs).  
    * **Stripe:** sk\_test\_000000000000000000000000 (Stripe keys usually start with sk\_live\_ or sk\_test\_).  
* **Step 1.3: Develop the Basic Injector Script (injector.py)**  
  * **Action:** Create a file named injector.py in your project root.  
  * **Code Implementation:**  
    from mitmproxy import http

    class Injector:  
        def request(self, flow: http.HTTPFlow):  
            \# Check if the header exists  
            auth\_header \= flow.request.headers.get("Authorization", "")

            \# Logic: If we see the dummy Stripe key, swap it for the real one  
            if "sk\_test\_00000000" in auth\_header:  
                print(f"\[+\] Intercepted Dummy Stripe Key. Injecting Real Key...")  
                \# REPLACE THIS with your actual test key for now, later we use env vars  
                real\_key \= "sk\_test\_REAL\_KEY\_HERE"   
                flow.request.headers\["Authorization"\] \= f"Bearer {real\_key}"

    addons \= \[Injector()\]

* **Step 1.4: Run and Test Locally**  
  * Action: Start mitmproxy in "Regular" mode listening on port 8080:  
    mitmdump \-s injector.py \-p 8080  
  * Action: In a separate terminal window, try to use the proxy using curl.  
    export HTTP\_PROXY=http://localhost:8080  
    export HTTPS\_PROXY=http://localhost:8080  
    curl \-H "Authorization: Bearer sk\_test\_00000000" http://httpbin.org/headers  
  * **Verification:** Look at the curl output. The Authorization header returned by httpbin should show your **REAL** key, not the dummy one.  
* **Step 1.5: Establish Trust (The SSL Problem)**  
  * **Context:** HTTPS traffic will fail because your computer doesn't trust the proxy.  
  * **Action:** When you ran mitmdump the first time, it generated certificates in \~/.mitmproxy/.  
  * **Action:** Install the certificate:  
    * **Mac:** open \~/.mitmproxy/mitmproxy-ca-cert.pem \-\> Keychain Access \-\> Double click \-\> Trust \-\> "Always Trust".  
    * **Linux:** Copy to /usr/local/share/ca-certificates/ and run update-ca-certificates.  
  * **Test:** Run curl https://api.stripe.com/v1/charges ... (using a dummy key) and ensure you don't get an SSL error.

## **Phase 2: Transparent Interception & Dockerization**

**Goal:** Move everything into Docker containers so the application (AI Agent) doesn't need to know a proxy exists. We stop using HTTP\_PROXY variables.

* **Step 2.1: The Proxy Dockerfile**  
  * **Action:** Create proxy/Dockerfile.  
  * **Content:**  
    FROM mitmproxy/mitmproxy:latest  
    \# Install python dependencies for our script  
    RUN pip install boto3 requests  
    \# Copy our script  
    COPY injector.py /home/mitmproxy/injector.py  
    \# Entry command: Run in transparent mode  
    CMD \["mitmdump", "--mode", "transparent", "--showhost", "-s", "/home/mitmproxy/injector.py"\]

* **Step 2.2: The Network Architecture (Docker Compose)**  
  * **Action:** Create docker-compose.yml.  
  * **Critical Detail:** We use network\_mode: service:proxy. This forces the App container to share the *exact same network stack* (IP address and ports) as the Proxy container.  
  * **Content:**  
    services:  
      proxy:  
        build: ./proxy  
        privileged: true  \# Required for iptables  
        cap\_add:  
          \- NET\_ADMIN  
        volumes:  
          \- ./certs:/certs  \# Share certs with host/app  
        command: \>  
          sh \-c "iptables \-t nat \-A OUTPUT \-p tcp \-m owner \! \--uid-owner mitmproxy \-m multiport \--dports 80,443 \-j REDIRECT \--to-port 8080 &&  
                 mitmdump \--mode transparent \--showhost \-s /home/mitmproxy/injector.py"

      app:  
        image: python:3.10-slim  
        network\_mode: service:proxy  \# \<--- THE MAGIC SAUCE  
        depends\_on:  
          \- proxy  
        command: sleep infinity \# Just keep it running for testing

* **Step 2.3: The iptables Explanation**  
  * **Concept:** The command iptables \-t nat \-A OUTPUT... is a rule that says "Any TCP traffic leaving this container on port 80 or 443 should be grabbed and thrown into port 8080 (our proxy)."  
  * **Safety:** The part \! \--uid-owner mitmproxy is crucial. It prevents the proxy's *own* traffic from getting caught in a loop.  
* **Step 2.4: Distributing the Certificate Automatically**  
  * **Problem:** The app container is fresh and doesn't trust the proxy.  
  * **Action:** Update the app definition in docker-compose to mount the certs and install them on startup.  
  * Revised App Command:  
    command: sh \-c "cp /certs/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && update-ca-certificates && sleep infinity"

## **Phase 3: Advanced Protocol Implementation (AWS SigV4)**

**Goal:** Handle the complex AWS signing process. This is the hardest part because you cannot just swap a header; you must re-sign the entire request.

* **Step 3.1: Prepare the AWS Injector Logic**  
  * **Action:** Edit injector.py to import AWS libraries.  
    import boto3  
    from botocore.auth import SigV4Auth  
    from botocore.awsrequest import AWSRequest  
    from botocore.credentials import Credentials

* **Step 3.2: Implement the "Re-Signing" Function**  
  * **Concept:** When a request comes in, we strip the old signature (dummy), load the real keys, and calculate a new signature.  
  * **Action:** Add this function to your class:  
    def sign\_aws\_request(self, flow, real\_access\_key, real\_secret\_key, region, service):  
        \# 1\. Create a Botocore AWSRequest object from the flow  
        req \= AWSRequest(  
            method=flow.request.method,  
            url=flow.request.url,  
            data=flow.request.content,  
            headers=flow.request.headers  
        )

        \# 2\. Create Credentials object  
        creds \= Credentials(real\_access\_key, real\_secret\_key)

        \# 3\. Create Signer and Sign  
        SigV4Auth(creds, service, region).add\_auth(req)

        \# 4\. Copy signed headers back to the original flow  
        for k, v in req.headers.items():  
            flow.request.headers\[k\] \= v

* **Step 3.3: Handle the "UNSIGNED-PAYLOAD" Optimization**  
  * **Why:** If you upload a 1GB file to S3, the proxy shouldn't try to buffer all 1GB to calculate a hash.  
  * **Action:** Inside your signing logic, force the header x-amz-content-sha256 to be UNSIGNED-PAYLOAD for S3 requests. This tells AWS "trust the SSL connection, don't verify the body hash."

## **Phase 4: Production Hardening & Secrets**

**Goal:** Stop hardcoding keys in injector.py.

* **Step 4.1: Environment Variable Injection**  
  * Action: In injector.py, replace hardcoded strings with:  
    os.environ.get("AWS\_ACCESS\_KEY\_ID")  
  * **Action:** In docker-compose.yml, add an env\_file directive or an environment section under the proxy service.  
  * **Human Intervention:** You must create a .env file on your host machine containing the REAL credentials. **Add .env to .gitignore immediately.**  
* **Step 4.2: Configuration File (config.yaml)**  
  * **Action:** Create a config.yaml to map dummy keys to strategies.  
    mappings:  
      \- dummy: "AKIA00000000DUMMYKEY"  
        provider: "aws"  
        secret\_env\_prefix: "AWS\_PROD"  
      \- dummy: "sk\_test\_00000000"  
        provider: "stripe"  
        secret\_env: "STRIPE\_LIVE\_KEY"

  * **Action:** Update injector.py to load this YAML at startup (def load(self, loader):).

## **Phase 5: Agentic Workflow (Dev Containers)**

**Goal:** Allow an AI Agent (like Claude or Cline) to work inside this environment seamlessly.

* **Step 5.1: Create DevContainer Config**  
  * **Action:** Create .devcontainer/devcontainer.json.  
  * **Content:**  
    {  
      "name": "Secure Agent Sandbox",  
      "dockerComposeFile": "../docker-compose.yml",  
      "service": "app",  
      "workspaceFolder": "/workspace",  
      "features": {  
        "ghcr.io/devcontainers/features/python:1": {}  
      },  
      // CRITICAL: Mount the certificate so VS Code/Agents trust it  
      "postCreateCommand": "cp /certs/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && update-ca-certificates"  
    }

* **Step 5.2: Launching**  
  * **Action:** Open VS Code. Press F1 \-\> "Dev Containers: Reopen in Container".  
  * **Result:** VS Code will build the proxy and app, link them, set up the iptables rules, and drop you into a terminal in the app container.  
  * **Test:** Run aws s3 ls using the dummy key. It should work, listing your real S3 buckets.