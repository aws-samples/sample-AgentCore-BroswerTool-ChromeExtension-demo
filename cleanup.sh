#!/bin/bash
# Cleanup script for AgentCore Browser Extension Demo

set -e

echo "🧹 Cleaning up resources..."
echo ""

# Function to ask for confirmation
confirm() {
    read -p "$1 [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Clean up S3 bucket
if confirm "Delete S3 bucket (browser-extension-demo-zihangh-20260129)?"; then
    echo "Deleting S3 bucket..."
    aws s3 rb s3://browser-extension-demo-zihangh-20260129 --force 2>/dev/null && \
        echo "✓ S3 bucket deleted" || \
        echo "⚠ Bucket not found or already deleted"
    echo ""
fi

# Clean up local files
if confirm "Delete local temporary files?"; then
    echo "Deleting local files..."
    
    # Remove directories
    rm -rf stealth_extension/ 2>/dev/null && echo "✓ Removed stealth_extension/"
    rm -rf amazon-bedrock-summary-client-for-chrome/ 2>/dev/null && echo "✓ Removed amazon-bedrock-summary-client-for-chrome/"
    rm -rf __pycache__/ 2>/dev/null && echo "✓ Removed __pycache__/"
    rm -rf .pytest_cache/ 2>/dev/null && echo "✓ Removed .pytest_cache/"
    
    # Remove zip files
    rm -f stealth-extension.zip 2>/dev/null && echo "✓ Removed stealth-extension.zip"
    rm -f bedrock-summary-extension*.zip 2>/dev/null && echo "✓ Removed bedrock-summary-extension*.zip"
    
    echo ""
fi

echo "✅ Cleanup complete!"
echo ""
echo "Note: Browser sessions need to be stopped manually or will timeout automatically."
echo "To stop a session: aws bedrock-agentcore stop-browser-session --session-id <SESSION_ID> --region us-east-1"
