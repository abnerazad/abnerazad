# GitHub Profile ASCII Art & Dynamic Stats Setup Guide

This guide walks you through setting up and deploying your automated ASCII art & dynamic stats dashboard (inspired by [Andrew6rant](https://github.com/Andrew6rant/Andrew6rant)).

---

## 📁 Repository Structure

```text
├── .github/
│   └── workflows/
│       └── build.yaml          # Automatically runs daily to update your stats
├── cache/
│   └── requirements.txt        # Python dependencies
├── ascii_generator.py          # Convert any image/photo to ASCII art & update SVGs
├── today.py                    # GitHub GraphQL stats engine with cache
├── dark_mode.svg               # Dark theme ASCII art + Neofetch terminal stats
├── light_mode.svg              # Light theme ASCII art + Neofetch terminal stats
├── README.md                   # Profile README displaying the SVG
└── setup_guide.md              # This setup guide
```

---

## 🚀 Quick Setup in 4 Steps

### Step 1: Create Your Profile Repository
1. Create a new public repository on GitHub named **exactly your GitHub username** (e.g. if your username is `octocat`, name the repository `octocat`).
2. Push all the files from this directory to the repository's `main` branch.

```bash
git init
git add .
git commit -m "Initial commit of GitHub Profile ASCII Dashboard"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_USERNAME>.git
git push -u origin main
```

---

### Step 2: Create a GitHub Personal Access Token (PAT)
1. Go to **[GitHub Token Settings](https://github.com/settings/tokens)**.
2. Select **Generate new token** (Classic) or **Fine-grained token**:
   - For **Classic Token**:
     - Check: `repo` (all), `read:user`, `user:email`
   - For **Fine-grained Token**:
     - Repository access: **All repositories**
     - Account permissions: `Read-only` for **Followers**, **Starring**, **Watching**
     - Repository permissions: `Read-only` for **Contents**, **Commit statuses**, **Metadata**
3. Copy the generated token string.

---

### Step 3: Add Repository Secrets
1. In your profile repository on GitHub, navigate to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add:
   - Name: `ACCESS_TOKEN` | Value: *(Paste your Personal Access Token)*
   - Name: `USER_NAME` | Value: *(Your GitHub username)*

---

### Step 4: Enable Workflow Write Permissions
1. In your repository, go to **Settings** > **Actions** > **General**.
2. Under **Workflow permissions**, choose **Read and write permissions**.
3. Check the box **"Allow GitHub Actions to create and approve pull requests"**.
4. Click **Save**.

---

## 🎨 How to Customize Your Profile

### 1. Change Personal Info (OS, IDE, Languages, Socials)
Open `dark_mode.svg` and `light_mode.svg` in any text editor and change any of the text values in lines 47–65 (e.g., your OS, kernel, IDE, languages, contact emails, Discord, LinkedIn).

> **Tip**: Keep the `. ........................ ` dot leaders aligned with the text so the terminal look remains neat.

### 2. Configure Your Birthday / Uptime
In `today.py`, adjust lines 18–20:
```python
BIRTH_YEAR = 2002
BIRTH_MONTH = 7
BIRTH_DAY = 5
```
Or set `BIRTH_YEAR`, `BIRTH_MONTH`, `BIRTH_DAY` as repository Secrets/Environment variables.

### 3. Generate Custom ASCII Art From Your Own Photo
You can convert any image (portrait, avatar, anime mascot, logo) directly into the SVGs:

```bash
# Install requirements locally
pip install -r cache/requirements.txt

# Convert image and automatically update both dark_mode.svg and light_mode.svg
python ascii_generator.py --image path/to/your_photo.jpg --update-svgs
```

**Options for `ascii_generator.py`:**
- `--image`, `-i`: Path to your image file (`.png`, `.jpg`, `.webp`)
- `--contrast`, `-c`: Adjust contrast (default: `1.4`)
- `--brightness`, `-b`: Adjust brightness (default: `1.0`)
- `--invert`: Invert dark/light tones
- `--update-svgs`: Write the generated ASCII directly into `dark_mode.svg` and `light_mode.svg`

---

## 🧪 Testing Locally

You can test `today.py` anytime on your machine:

```bash
# Test in offline/mock mode (no token needed)
python today.py

# Test with live GitHub stats
$env:ACCESS_TOKEN="ghp_yourtoken..."
$env:USER_NAME="your_username"
python today.py
```
