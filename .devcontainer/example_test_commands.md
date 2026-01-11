# Ensure .env has HF_TOKEN={HF_TOKEN} and .env.vault has credential HF_TOKEN=<API_KEY>
curl https://huggingface.co/api/whoami-v2 -H "Authorization: Bearer HF_TOKEN"
