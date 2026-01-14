# Semantic Scholar API Setup Guide

This guide walks you through setting up Semantic Scholar API credentials with CloakCode.

---

## Overview

Semantic Scholar is an AI-powered research tool that provides access to a large corpus of scientific literature. The API allows you to search papers, get recommendations, and access citation data.

**Time required:** ~5 minutes

---

## Step 1: Get Your API Key

### Sign Up for API Access

1. Go to: **https://www.semanticscholar.org/product/api**
2. Click "Request API Key"
3. Fill out the form with:
   - Your name
   - Email address
   - Organization
   - Intended use case
4. Wait for email confirmation (usually within 24 hours)
5. Your API key will be in the email

**API Key Format:** Usually a long alphanumeric string

---

## Step 2: Add to CloakCode

### Option 1: Environment Variable

```bash
# Edit .env file
nano .env

# Add your key
S2_API_KEY=your-actual-semantic-scholar-api-key
```

### Option 2: Using the Setup Script

```bash
./scripts/add-credential.sh

# Select: Custom/Other
# Service name: Semantic Scholar
# Token env var: S2_API_KEY
# Paste your API key when prompted
```

---

## Step 3: Configure Proxy (Already Done!)

The configuration is already in `proxy/config.yaml.example`:

```yaml
strategies:
  - name: semantic-scholar
    type: bearer
    config:
      token: S2_API_KEY
      dummy_pattern: "DUMMY_S2_API_KEY"
      allowed_hosts:
        - "api.semanticscholar.org"
        - "*.semanticscholar.org"

rules:
  - name: semantic-scholar-injection
    domain_regex: "^(.*\\.)?semanticscholar\\.org$"
    trigger_header_regex: "DUMMY_S2_API_KEY"
    strategy: semantic-scholar
    priority: 100
```

If you copied `config.yaml.example` to `config.yaml`, this is already configured!

---

## Step 4: Usage Examples

### Python Example

```python
import requests

# Use dummy API key - CloakCode will inject the real one
headers = {
    "x-api-key": "DUMMY_S2_API_KEY"
}

# Search for papers
response = requests.get(
    "https://api.semanticscholar.org/graph/v1/paper/search",
    headers=headers,
    params={
        "query": "machine learning",
        "limit": 10,
        "fields": "title,authors,year,citationCount"
    }
)

papers = response.json()
for paper in papers.get('data', []):
    print(f"{paper['title']} ({paper['year']})")
```

### Python with S2 SDK

```python
from semanticscholar import SemanticScholar

# Use dummy key - CloakCode injects real one
sch = SemanticScholar(api_key="DUMMY_S2_API_KEY")

# Get paper details
paper = sch.get_paper('10.1038/nature14539')
print(f"Title: {paper.title}")
print(f"Authors: {', '.join([a.name for a in paper.authors])}")
print(f"Citations: {paper.citationCount}")

# Search papers
results = sch.search_paper("neural networks", limit=5)
for paper in results:
    print(f"- {paper.title} ({paper.year})")
```

### Node.js Example

```javascript
const axios = require('axios');

// Use dummy API key
const headers = {
  'x-api-key': 'DUMMY_S2_API_KEY'
};

// Get paper by ID
axios.get(
  'https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b',
  {
    headers,
    params: {
      fields: 'title,authors,year,abstract,citationCount'
    }
  }
)
.then(response => {
  const paper = response.data;
  console.log(`Title: ${paper.title}`);
  console.log(`Year: ${paper.year}`);
  console.log(`Citations: ${paper.citationCount}`);
})
.catch(error => {
  console.error('Error:', error.message);
});
```

### cURL Example

```bash
# Search for papers
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=deep+learning&limit=5" \
  -H "x-api-key: DUMMY_S2_API_KEY"

# Get paper details
curl "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b?fields=title,authors,year" \
  -H "x-api-key: DUMMY_S2_API_KEY"

# Get paper citations
curl "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations?limit=10" \
  -H "x-api-key: DUMMY_S2_API_KEY"
```

---

## API Endpoints

### Common Endpoints

| Endpoint | Description |
|----------|-------------|
| `/graph/v1/paper/search` | Search papers |
| `/graph/v1/paper/{paperId}` | Get paper details |
| `/graph/v1/paper/{paperId}/citations` | Get paper citations |
| `/graph/v1/paper/{paperId}/references` | Get paper references |
| `/graph/v1/author/{authorId}` | Get author details |
| `/graph/v1/author/search` | Search authors |

### Paper ID Formats

Semantic Scholar accepts multiple ID formats:
- **S2 ID**: `649def34f8be52c8b66281af98ae884c09aef38b`
- **DOI**: `10.1038/nature14539`
- **ArXiv ID**: `arXiv:1705.10311`
- **PubMed ID**: `PMID:12345678`

---

## API Limits

### Free Tier (No API Key)
- 100 requests per 5 minutes
- Basic data only

### With API Key
- 1000+ requests per 5 minutes (varies by use case)
- Access to full dataset
- Priority support

**Rate Limit Headers:**
```
x-ratelimit-limit: 100
x-ratelimit-remaining: 95
x-ratelimit-reset: 1234567890
```

---

## Verifying Setup

### Test 1: Simple Request

```python
import requests

response = requests.get(
    "https://api.semanticscholar.org/graph/v1/paper/search",
    headers={"x-api-key": "DUMMY_S2_API_KEY"},
    params={"query": "attention is all you need", "limit": 1}
)

if response.status_code == 200:
    print("✅ Semantic Scholar API working!")
    print(f"Found: {response.json()['data'][0]['title']}")
else:
    print(f"❌ Error: {response.status_code}")
```

### Test 2: Check Logs

```bash
# Monitor credential injection
tail -f logs/proxy_injections.log

# You should see:
# [2026-01-14 14:15:00] INJECTION: api.semanticscholar.org
#   Trigger: DUMMY_S2_API_KEY detected
#   Strategy: semantic-scholar
#   Status: SUCCESS
```

---

## Best Practices

### 1. Rate Limiting
```python
import time

def search_with_backoff(query):
    max_retries = 3
    for attempt in range(max_retries):
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            headers={"x-api-key": "DUMMY_S2_API_KEY"},
            params={"query": query}
        )
        
        if response.status_code == 429:  # Rate limited
            wait_time = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

### 2. Batch Requests
```python
# Get multiple papers efficiently
paper_ids = ['id1', 'id2', 'id3']
papers = []

for paper_id in paper_ids:
    response = requests.get(
        f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}",
        headers={"x-api-key": "DUMMY_S2_API_KEY"},
        params={"fields": "title,year,authors"}
    )
    papers.append(response.json())
    time.sleep(0.1)  # Be nice to the API
```

### 3. Error Handling
```python
def safe_api_call(endpoint, **kwargs):
    try:
        response = requests.get(
            f"https://api.semanticscholar.org{endpoint}",
            headers={"x-api-key": "DUMMY_S2_API_KEY"},
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Paper not found: {endpoint}")
        elif e.response.status_code == 429:
            print("Rate limit exceeded")
        else:
            print(f"HTTP error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
```

---

## Troubleshooting

### Error: 401 Unauthorized

**Problem:** API key invalid or not injected

**Solutions:**
1. Check `.env` has `S2_API_KEY=your-real-key`
2. Restart proxy: `docker-compose restart proxy`
3. Verify dummy pattern: `DUMMY_S2_API_KEY`
4. Check logs: `docker logs cloakcode_proxy`

### Error: 429 Too Many Requests

**Problem:** Rate limit exceeded

**Solutions:**
1. Check rate limit headers
2. Implement exponential backoff
3. Request higher rate limits from Semantic Scholar
4. Spread requests over time

### API Key Not Working

**Problem:** Key not being injected

**Solutions:**
1. Verify configuration in `proxy/config.yaml`
2. Check domain regex matches: `^(.*\\.)?semanticscholar\\.org$`
3. Ensure dummy pattern matches: `DUMMY_S2_API_KEY`
4. Restart proxy after config changes

---

## Resources

- **API Documentation**: https://api.semanticscholar.org/api-docs/
- **API Key Request**: https://www.semanticscholar.org/product/api#api-key
- **Python SDK**: https://github.com/danielnsilva/semanticscholar
- **Rate Limits**: https://api.semanticscholar.org/api-docs/rate-limits
- **Support**: api-support@semanticscholar.org

---

## Quick Reference

```bash
# Environment Variable
S2_API_KEY=your-api-key

# Dummy Pattern
DUMMY_S2_API_KEY

# API Base URL
https://api.semanticscholar.org

# Header
x-api-key: DUMMY_S2_API_KEY

# Test Command
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=test" \
  -H "x-api-key: DUMMY_S2_API_KEY"
```

---

**Last Updated:** 2026-01-14  
**Version:** 1.0
