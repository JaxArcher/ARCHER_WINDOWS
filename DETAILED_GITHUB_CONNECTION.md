# Detailed GitHub Connection Instructions for ARCHER_WINDOWS

## Step 2: Connecting to GitHub - Complete Guide

### What You'll Need:
- GitHub account (you already have this)
- GitHub username (yours is likely "cjax1215" based on your email)
- GitHub password or personal access token
- Internet connection

### Method 1: Manual Connection (Recommended for First Time)

#### Step 2.1: Create GitHub Repository
1. Open your web browser
2. Go to: https://github.com/new
3. You should see "Create a new repository" page
4. Fill in the form:
   - **Repository name**: `ARCHER_WINDOWS`
   - **Description** (optional): "ARCHER AI Windows Project"
   - **Public/Private**: Choose `Private` (recommended for development)
   - **Initialize this repository with**: Leave all unchecked (we already have files)
5. Click the green "Create repository" button

#### Step 2.2: Copy the Repository URL
After creating the repository, you'll see a page with quick setup instructions.
Look for the section that says:

```
…or push an existing repository from the command line
```

You'll see two URLs - one for HTTPS and one for SSH. Choose HTTPS for now.

#### Step 2.3: Open PowerShell or Command Prompt
1. Press `Win + R` on your keyboard
2. Type `powershell` (recommended) or `cmd` and press Enter
3. This opens PowerShell (preferred) or Command Prompt

#### Step 2.4: Navigate to ARCHER_WINDOWS Directory

**In PowerShell (recommended):**
```powershell
cd D:\ARCHER_WINDOWS
```

**In Command Prompt:**
```cmd
cd /d D:\ARCHER_WINDOWS
```

(If you're on a different drive, adjust accordingly)

#### Step 2.5: Add GitHub as Remote
Type this command (replace `your-username` with your actual GitHub username):
```
git remote add origin https://github.com/your-username/ARCHER_WINDOWS.git
```

For example, if your username is "cjax1215":
```
git remote add origin https://github.com/cjax1215/ARCHER_WINDOWS.git
```

#### Step 2.6: Rename Branch to Main
```
git branch -M main
```

#### Step 2.7: Push to GitHub
```
git push -u origin main
```

#### Step 2.8: Authentication
When you run the push command, you'll be prompted for:
1. **Username**: Your GitHub username
2. **Password**: Your GitHub password OR personal access token

**Important**: If you have 2FA enabled (recommended), you MUST use a personal access token instead of your password.

### Method 2: Using the Automated Script

#### Step 2.1: Open Command Prompt
Press `Win + R`, type `cmd`, press Enter

#### Step 2.2: Navigate to ARCHER_WINDOWS
```
cd /d D:\ARCHER_WINDOWS
```

#### Step 2.3: Run the Script
```
connect_to_github.sh
```

#### Step 2.4: Follow the Prompts
The script will ask you:
1. **GitHub username**: Enter your GitHub username (e.g., cjax1215)
2. **Repository name**: Press Enter to use "ARCHER_WINDOWS" or type a different name
3. **Connection method**: Press Enter for HTTPS or type 2 for SSH

#### Step 2.5: Authentication
When the script runs `git push`, you'll be prompted for:
- Username: Your GitHub username
- Password: Your GitHub password or personal access token

### Troubleshooting Authentication

#### If You Get Authentication Errors:

**Option A: Use Personal Access Token (Recommended)**
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` permissions
3. Use this token as your "password" when Git asks for it

**Option B: Use SSH Instead**
1. Set up SSH keys on your computer
2. Add the public key to your GitHub account
3. Use the SSH URL: `git@github.com:your-username/ARCHER_WINDOWS.git`

### Verifying the Connection

After successful connection, verify with:
```
git remote -v
```

You should see:
```
origin  https://github.com/your-username/ARCHER_WINDOWS.git (fetch)
origin  https://github.com/your-username/ARCHER_WINDOWS.git (push)
```

### Common Issues and Solutions

**Issue 1**: "Repository not found"
- **Solution**: Make sure the repository name matches exactly (case-sensitive)

**Issue 2**: "Authentication failed"
- **Solution**: Use a personal access token instead of password

**Issue 3**: "Branch 'main' not found"
- **Solution**: Run `git branch -M main` first

**Issue 4**: "Permission denied (publickey)"
- **Solution**: Either use HTTPS or set up SSH keys properly

### After Successful Connection

Your ARCHER_WINDOWS project is now on GitHub! Here's what to do next:

1. **Check GitHub**: Refresh your repository page - you should see all your files
2. **Normal Workflow**:
   ```bash
   # Make changes to files
   git add .
   git commit -m "Your descriptive message"
   git push
   ```

3. **Pull Changes** (if working with others):
   ```bash
   git pull
   ```

### Additional Tips

- **Commit Messages**: Write clear, descriptive commit messages
- **Frequency**: Commit often with small, logical changes
- **Branches**: Consider using branches for new features
- **README**: Your README.md will be displayed on GitHub automatically

### Need More Help?

If you encounter any issues, check:
- The error message carefully
- Your internet connection
- Your GitHub username and repository name
- Your authentication method

You can also refer to:
- `GITHUB_CONNECTION_GUIDE.md` for basic instructions
- GitHub's official documentation for troubleshooting