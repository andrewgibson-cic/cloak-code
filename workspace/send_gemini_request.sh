#!/bin/bash

# Replace with your actual API key
API_KEY="DUMMY_GEMINI_KEY"

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key=${API_KEY}" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d '{
      "contents": [{
        "parts":[{
          "text": "Explain how AI works in one sentence."
        }]
      }]
    }'
