# Git Setup Instructions for EliteX

## Step 1: Initialize Git Repository Locally

Open your terminal and navigate to your project directory:

```bash
cd "/Users/anindyachakrabarty/Desktop/Application/Client Room"
```

Initialize git:
```bash
git init
```

## Step 2: Add Files to Git

Add all files (respecting .gitignore):
```bash
git add .
```

Check what will be committed:
```bash
git status
```

## Step 3: Create Your First Commit

```bash
git commit -m "Initial commit: EliteX V8 multi-agent wealth management system"
```

## Step 4: Connect to GitHub Repository

Replace `YOUR_USERNAME` with your GitHub username and `REPO_NAME` with your repository name:

```bash
git remote add origin https://github.com/AnindyaChakrabartyFAB/EliteX.git
```

Verify the remote:
```bash
git remote -v
```

## Step 5: Create Main Branch and Push

Rename branch to 'main' (GitHub standard):
```bash
git branch -M main
```

Push to GitHub:
```bash
git push -u origin main
```

**Note**: You'll be prompted for your GitHub credentials. If you have 2FA enabled, you'll need to use a Personal Access Token instead of your password.

## Creating a Personal Access Token (if needed)

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "EliteX Local Development"
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)
7. Use this token as your password when pushing

## Useful Git Commands for Future Updates

### Check current status
```bash
git status
```

### Add specific files
```bash
git add filename.py
```

### Add all changed files
```bash
git add .
```

### Commit changes
```bash
git commit -m "Description of changes"
```

### Push changes to GitHub
```bash
git push
```

### Pull latest changes from GitHub
```bash
git pull
```

### Create a new branch
```bash
git checkout -b feature-branch-name
```

### Switch between branches
```bash
git checkout main
git checkout feature-branch-name
```

### View commit history
```bash
git log --oneline
```

## Important Notes

✅ **The .gitignore file prevents sensitive data from being pushed** (client data, credentials, logs, etc.)

✅ **Always check `git status` before committing** to ensure you're not accidentally adding sensitive files

✅ **Use meaningful commit messages** like:
   - "Add new risk assessment agent"
   - "Fix CASA balance calculation bug"
   - "Update README with installation instructions"

✅ **Consider creating a .env.example file** for environment variables (without actual secrets)

## Troubleshooting

### If you get "remote origin already exists":
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

### If you accidentally committed sensitive data:
```bash
# Remove file from git but keep it locally
git rm --cached filename.ext
git commit -m "Remove sensitive file"
git push
```

### If push is rejected (non-fast-forward):
```bash
# Pull first, then push
git pull origin main --rebase
git push
```

## Creating Branches for Features

Good practice: Use branches for new features

```bash
# Create and switch to new branch
git checkout -b feature/new-agent

# Make your changes, then commit
git add .
git commit -m "Add new agent feature"

# Push branch to GitHub
git push -u origin feature/new-agent

# Later, merge to main
git checkout main
git merge feature/new-agent
git push
```

## Next Steps After Initial Push

1. ✅ Add repository description on GitHub
2. ✅ Add topics/tags (ai, wealth-management, fintech, multi-agent)
3. ✅ Enable GitHub Issues for bug tracking
4. ✅ Set up branch protection rules for 'main'
5. ✅ Consider adding GitHub Actions for CI/CD
6. ✅ Add collaborators if working in a team

---

**Your code is now on GitHub!** 🎉

