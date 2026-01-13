#!/bin/bash
# Logging Utilities for CloakCode Agent Container
# Provides persistent, structured logging for agent activities

# Configuration
LOG_DIR="${LOG_DIR:-/home/agent/logs}"
ACTIVITY_LOG="${LOG_DIR}/agent_activity.log"
AUDIT_LOG="${LOG_DIR}/audit.json"
MAX_LOG_SIZE=$((50 * 1024 * 1024))  # 50MB

# Ensure log directory exists
ensure_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR" 2>/dev/null || sudo mkdir -p "$LOG_DIR"
        chmod 755 "$LOG_DIR" 2>/dev/null || sudo chmod 755 "$LOG_DIR"
    fi
    
    # Create log files if they don't exist
    touch "$ACTIVITY_LOG" "$AUDIT_LOG" 2>/dev/null || true
}

# Rotate log if it exceeds size limit
rotate_log_if_needed() {
    local log_file="$1"
    
    if [ -f "$log_file" ]; then
        local size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0)
        if [ "$size" -gt "$MAX_LOG_SIZE" ]; then
            local timestamp=$(date +%Y%m%d_%H%M%S)
            mv "$log_file" "${log_file}.${timestamp}"
            gzip "${log_file}.${timestamp}" 2>/dev/null &
            touch "$log_file"
        fi
    fi
}

# Log a plain text event
log_event() {
    ensure_log_dir
    rotate_log_if_needed "$ACTIVITY_LOG"
    
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] $*" | tee -a "$ACTIVITY_LOG"
}

# Log a structured JSON event
log_json_event() {
    ensure_log_dir
    rotate_log_if_needed "$AUDIT_LOG"
    
    local event_type="$1"
    shift
    
    local timestamp=$(date -Iseconds)
    local json_line=$(cat <<EOF
{"timestamp":"$timestamp","event_type":"$event_type","data":{"message":"$*"}}
EOF
)
    echo "$json_line" >> "$AUDIT_LOG"
}

# Log command with output capture
log_command() {
    local cmd_name="$1"
    shift
    local args="$*"
    
    log_event "$cmd_name: $args"
    log_json_event "command_execution" "$cmd_name $args"
}

# Wrapper for npm commands
npm_logged() {
    log_command "NPM" "$@"
    command npm "$@" 2>&1 | tee -a "$ACTIVITY_LOG"
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -ne 0 ]; then
        log_event "ERROR: npm command failed with exit code $exit_code"
        log_json_event "npm_error" "Command failed: npm $*"
    fi
    
    return $exit_code
}

# Wrapper for pip commands
pip_logged() {
    log_command "PIP" "$@"
    command pip "$@" 2>&1 | tee -a "$ACTIVITY_LOG"
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -ne 0 ]; then
        log_event "ERROR: pip command failed with exit code $exit_code"
        log_json_event "pip_error" "Command failed: pip $*"
    fi
    
    return $exit_code
}

# Wrapper for git commands
git_logged() {
    log_command "GIT" "$@"
    command git "$@" 2>&1 | tee -a "$ACTIVITY_LOG"
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -ne 0 ]; then
        log_event "ERROR: git command failed with exit code $exit_code"
        log_json_event "git_error" "Command failed: git $*"
    else
        # Log specific git operations
        case "$1" in
            clone)
                log_json_event "git_clone" "Repository: $2"
                ;;
            push)
                log_json_event "git_push" "Remote: ${2:-origin}"
                ;;
            pull)
                log_json_event "git_pull" "Remote: ${2:-origin}"
                ;;
        esac
    fi
    
    return $exit_code
}

# Wrapper for sudo commands (security-sensitive)
sudo_logged() {
    log_event "SUDO: $*"
    log_json_event "sudo_execution" "$*"
    command sudo "$@"
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        log_event "ERROR: sudo command failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Log container startup
log_container_start() {
    log_event "=========================================="
    log_event "Container Started"
    log_event "User: $(whoami)"
    log_event "Hostname: $(hostname)"
    log_event "Working Directory: $(pwd)"
    log_event "=========================================="
    
    log_json_event "container_start" "Container initialization complete"
}

# Log container shutdown
log_container_stop() {
    log_event "=========================================="
    log_event "Container Stopping"
    log_event "=========================================="
    
    log_json_event "container_stop" "Container shutdown initiated"
}

# Setup bash history logging
setup_bash_history_logging() {
    # Save history to persistent location
    export HISTFILE="${LOG_DIR}/.bash_history"
    export HISTSIZE=10000
    export HISTFILESIZE=10000
    export HISTTIMEFORMAT="%Y-%m-%d %H:%M:%S "
    export HISTCONTROL=ignoredups:erasedups
    
    # Append to history file immediately
    shopt -s histappend
    
    # Log commands before execution
    export PROMPT_COMMAND="history -a; ${PROMPT_COMMAND}"
}

# Export functions for use in interactive shells
export -f log_event
export -f log_json_event
export -f log_command
export -f npm_logged
export -f pip_logged
export -f git_logged
export -f sudo_logged

# Setup aliases for common commands
alias npm='npm_logged'
alias pip='pip_logged'
alias pip3='pip_logged'
alias git='git_logged'
alias sudo='sudo_logged'
