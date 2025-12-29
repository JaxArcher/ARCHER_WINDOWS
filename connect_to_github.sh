#!/bin/bash

# ARCHER_WINDOWS GitHub Connection Script

echo "ARCHER_WINDOWS GitHub Connection Script"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -d ".git" ]; then
    echo "Error: This script must be run from the ARCHER_WINDOWS directory"
    exit 1
fi

# Ask for GitHub username
read -p "Enter your GitHub username: " github_username

# Ask for repository name
read -p "Enter your GitHub repository name [ARCHER_WINDOWS]: " repo_name
repo_name=${repo_name:-ARCHER_WINDOWS}

# Ask for connection method
read -p "Use HTTPS (1) or SSH (2)? [1]: " connection_method
connection_method=${connection_method:-1}

if [ "$connection_method" = "1" ]; then
    # HTTPS
    remote_url="https://github.com/$github_username/$repo_name.git"
    echo "Using HTTPS: $remote_url"
else
    # SSH
    remote_url="git@github.com:$github_username/$repo_name.git"
    echo "Using SSH: $remote_url"
fi

# Add remote
git remote add origin "$remote_url"

# Rename branch to main
git branch -M main

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

echo ""
echo "Connection complete!"
echo "Verify with: git remote -v"

echo ""
echo "Future workflow:"
echo "1. Make changes to your files"
echo "2. git add ."
echo "3. git commit -m 'Your message'"
echo "4. git push"