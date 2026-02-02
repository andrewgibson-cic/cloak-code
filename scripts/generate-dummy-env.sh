#!/bin/bash
# Generate dummy .env for agent container
# Reads .env and replaces any non-DUMMY values with DUMMY versions

set -e

SOURCE_ENV="${1:-.env}"
TARGET_ENV="${2:-.env.agent}"

if [ ! -f "$SOURCE_ENV" ]; then
    echo "Error: Source .env file not found: $SOURCE_ENV"
    exit 1
fi

echo "# Auto-generated dummy .env for agent container" > "$TARGET_ENV"
echo "# Generated from: $SOURCE_ENV" >> "$TARGET_ENV"
echo "# All real credentials replaced with DUMMY values" >> "$TARGET_ENV"
echo "" >> "$TARGET_ENV"

# Process each line
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments
    if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        echo "$line" >> "$TARGET_ENV"
        continue
    fi
    
    # Parse key=value
    if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        
        # If value already contains DUMMY, keep it
        if [[ "$value" =~ DUMMY ]]; then
            echo "$line" >> "$TARGET_ENV"
            continue
        fi
        
        # If value is empty, keep it empty
        if [[ -z "$value" ]]; then
            echo "$line" >> "$TARGET_ENV"
            continue
        fi
        
        # Replace with appropriate DUMMY value based on key name
        case "$key" in
            *OPENAI*|*OPENAI_API_KEY*)
                echo "${key}=DUMMY_OPENAI_KEY" >> "$TARGET_ENV"
                ;;
            *ANTHROPIC*|*ANTHROPIC_API_KEY*)
                echo "${key}=DUMMY_ANTHROPIC_KEY" >> "$TARGET_ENV"
                ;;
            *GITHUB_TOKEN*|*GITHUB*PAT*)
                echo "${key}=DUMMY_GITHUB_TOKEN" >> "$TARGET_ENV"
                ;;
            *AWS_ACCESS_KEY*)
                echo "${key}=AKIA00000000DUMMYKEY" >> "$TARGET_ENV"
                ;;
            *AWS_SECRET*)
                echo "${key}=DUMMY_AWS_SECRET_KEY" >> "$TARGET_ENV"
                ;;
            *GEMINI*|*GOOGLE_API*)
                echo "${key}=DUMMY_GEMINI_KEY" >> "$TARGET_ENV"
                ;;
            *MISTRAL*)
                echo "${key}=DUMMY_MISTRAL_KEY" >> "$TARGET_ENV"
                ;;
            *STRIPE*)
                echo "${key}=sk_test_DUMMY_STRIPE" >> "$TARGET_ENV"
                ;;
            *SLACK_BOT*)
                echo "${key}=xoxb-DUMMY_SLACK_BOT" >> "$TARGET_ENV"
                ;;
            *SLACK_APP*)
                echo "${key}=xapp-DUMMY_SLACK_APP" >> "$TARGET_ENV"
                ;;
            *IBM*|*WATSONX*)
                echo "${key}=DUMMY_IBM_KEY" >> "$TARGET_ENV"
                ;;
            *S2_API_KEY*)
                echo "${key}=DUMMY_S2_API_KEY" >> "$TARGET_ENV"
                ;;
            *BINANCE*)
                echo "${key}=DUMMY_BINANCE_KEY" >> "$TARGET_ENV"
                ;;
            *TWILIO*)
                echo "${key}=DUMMY_TWILIO_TOKEN" >> "$TARGET_ENV"
                ;;
            *SENDGRID*)
                echo "${key}=DUMMY_SENDGRID_KEY" >> "$TARGET_ENV"
                ;;
            *DISCORD*)
                echo "${key}=DUMMY_DISCORD_TOKEN" >> "$TARGET_ENV"
                ;;
            *LOG_LEVEL*|*PROXY_PORT*|*REGION*|*BLOCK_*|*FAIL_*)
                # Keep configuration values as-is
                echo "$line" >> "$TARGET_ENV"
                ;;
            *)
                # Default: replace with generic DUMMY
                echo "${key}=DUMMY_${key}" >> "$TARGET_ENV"
                ;;
        esac
    else
        # Line doesn't match key=value, keep as-is
        echo "$line" >> "$TARGET_ENV"
    fi
done < "$SOURCE_ENV"

echo "✅ Generated dummy .env at: $TARGET_ENV"