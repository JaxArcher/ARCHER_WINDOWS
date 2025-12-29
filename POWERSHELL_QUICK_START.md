# PowerShell Quick Start Guide for GitHub Connection

## ✅ Recommended: Use PowerShell

PowerShell is the **modern** way to run commands on Windows and works perfectly with Git.

## 🚀 PowerShell Commands

### 1. Open PowerShell
```
Win + R → type "powershell" → Enter
```

### 2. Navigate to ARCHER_WINDOWS
```powershell
cd D:\ARCHER_WINDOWS
```

### 3. Connect to GitHub
```powershell
# Add GitHub as remote (replace your-username)
git remote add origin https://github.com/your-username/ARCHER_WINDOWS.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

### 4. Authentication
When prompted:
- **Username**: Your GitHub username
- **Password**: Your GitHub password or personal access token

## 💡 Why PowerShell is Better

✅ **No `/d` flag needed** - Simple `cd D:\path` works
✅ **Better tab completion** - Press Tab to autocomplete paths
✅ **Color output** - Git commands show in color
✅ **More powerful** - Full scripting capabilities
✅ **Modern** - Microsoft's recommended shell

## 🔄 Daily Workflow in PowerShell

```powershell
# Check status
git status

# Add all changes
git add .

# Commit with message
git commit -m "Your descriptive message"

# Push to GitHub
git push

# Pull latest changes
git pull
```

## 🎯 Quick Tips

- **Tab completion**: Start typing a path and press Tab
- **Clear screen**: `cls` or `Clear-Host`
- **List files**: `ls` or `dir`
- **Exit PowerShell**: `exit`

## 🐞 Troubleshooting

**If you get errors:**
- Make sure you're in the right directory: `pwd` (shows current path)
- Check GitHub connection: `git remote -v`
- Verify branch: `git branch`

**PowerShell vs Command Prompt:**
- Both work for Git commands
- PowerShell is more powerful and modern
- Use whichever you prefer - both will work!

## 🚀 Ready to Go!

Just open PowerShell, navigate to your project, and run the Git commands. It's that simple!