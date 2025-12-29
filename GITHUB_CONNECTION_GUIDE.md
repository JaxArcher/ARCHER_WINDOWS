# GitHub Connection Guide for ARCHER_WINDOWS

## Step 1: Create GitHub Repository
1. Go to https://github.com/new
2. Enter repository name: `ARCHER_WINDOWS`
3. Choose public or private (recommended: private for now)
4. Click "Create repository"

## Step 2: Connect Local Repository to GitHub

### Option A: Using HTTPS (easiest)
```bash
cd ARCHER_WINDOWS
git remote add origin https://github.com/your-username/ARCHER_WINDOWS.git
git branch -M main
git push -u origin main
```

### Option B: Using SSH (more secure)
```bash
cd ARCHER_WINDOWS
git remote add origin git@github.com:your-username/ARCHER_WINDOWS.git
git branch -M main
git push -u origin main
```

## Step 3: Authentication
- If using HTTPS, you'll be prompted for your GitHub username and password
- If using SSH, make sure you have SSH keys set up on GitHub

## Step 4: Verify Connection
```bash
git remote -v
```

This should show your GitHub repository URL.

## Troubleshooting

If you get authentication errors:
- For HTTPS: Use a personal access token instead of password
- For SSH: Make sure your SSH key is added to GitHub

## Future Workflow

After connecting, your normal workflow will be:
```bash
# Make changes to your files
git add .
git commit -m "Your commit message"
git push
```