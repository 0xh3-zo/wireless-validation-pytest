# 🚀 Setup Guide: Upload to GitHub

Follow these steps to get your repo on GitHub in under 5 minutes.

---

## ✅ Prerequisites

- Git installed ([download here](https://git-scm.com/downloads))
- GitHub account ([sign up here](https://github.com))

Check if git is installed:
```bash
git --version
```

---

## 📥 Step 1: Download All Files

Download these 7 files from Claude and put them in a new folder:

```
wireless-validation-pytest/
├── test_log_parser.py
├── requirements.txt
├── pytest.ini
├── README.md
├── .gitignore
├── LICENSE
└── sample_log.txt
```

---

## 🔧 Step 2: Initialize Local Repository

Open terminal/command prompt in your folder:

```bash
# Navigate to your folder
cd path/to/wireless-validation-pytest

# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: pytest framework for QXDM log analysis"
```

---

## 🌐 Step 3: Create GitHub Repository

1. Go to [github.com](https://github.com) and log in
2. Click the **+** icon (top right) → **New repository**
3. Fill in:
   - **Repository name:** `wireless-validation-pytest`
   - **Description:** "Automated pytest framework for 5G device validation from QXDM logs"
   - **Public** or **Private** (your choice)
   - **DO NOT** check "Add a README" (we already have one)
4. Click **Create repository**

---

## 🔗 Step 4: Connect Local to GitHub

GitHub will show you commands. Copy and paste these into your terminal:

```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR_USERNAME/wireless-validation-pytest.git

# Rename branch to main (if needed)
git branch -M main

# Push your code
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

---

## ✅ Step 5: Verify Upload

Go to your GitHub repo URL:
```
https://github.com/YOUR_USERNAME/wireless-validation-pytest
```

You should see:
- ✅ All 7 files uploaded
- ✅ README.md displaying as the repo homepage
- ✅ Green "main" branch indicator

---

## 🎨 Step 6: Polish (Optional But Recommended)

### Add Topics

On your repo page, click **⚙️ Settings** → scroll to **Topics** → add:
- `pytest`
- `wireless-testing`
- `5g-nr`
- `qxdm`
- `test-automation`
- `python`

### Update README with Your Info

Edit these lines in `README.md`:

```markdown
**Herbert Arbizo**  
Wireless Validation Engineer  
20+ years in cellular network testing

- 📧 Email: your.email@example.com        ← Change this
- 💼 LinkedIn: linkedin.com/in/your-name  ← Change this
- 🌐 Portfolio: your-website.com          ← Change this
```

Then commit and push:
```bash
git add README.md
git commit -m "Update author contact info"
git push
```

---

## 🧪 Step 7: Test It Works

Clone your repo somewhere else and run the tests:

```bash
# Clone to a new location
git clone https://github.com/YOUR_USERNAME/wireless-validation-pytest.git
cd wireless-validation-pytest

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_log_parser.py -v
```

All 12 tests should pass! ✅

---

## 🎯 Adding to Your Resume / LinkedIn

### Resume
```
Created automated pytest framework for 5G device validation
• Validates protocol logs against 3GPP standards (TS 38.133, TS 38.331)
• Detects handover failures, coverage holes, and KPI violations
• Reduces manual log analysis time from hours to seconds
• GitHub: github.com/YOUR_USERNAME/wireless-validation-pytest
```

### LinkedIn Post
```
🚀 Just published my pytest framework for wireless device validation!

Built for 5G NR testing, it automates:
✅ RF KPI validation (RSRP, RSRQ, SINR)
✅ Handover analysis with root cause detection
✅ Coverage hole identification
✅ 3GPP compliance checks

Perfect for validation engineers at Apple, Qualcomm, Samsung, etc.

Check it out: github.com/YOUR_USERNAME/wireless-validation-pytest

#wireless #5G #testing #python #pytest
```

---

## 🔄 Making Updates Later

When you improve your code:

```bash
# Make changes to files

# Stage changes
git add .

# Commit with message
git commit -m "Add support for multi-file log processing"

# Push to GitHub
git push
```

---

## 🌟 Pro Tips

### Add GitHub Actions Badge

Create `.github/workflows/tests.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest test_log_parser.py -v
```

Then add this badge to your README.md:
```markdown
![Tests](https://github.com/YOUR_USERNAME/wireless-validation-pytest/workflows/Tests/badge.svg)
```

### Pin Your Repo

On your GitHub profile, click **Customize your pins** and select this repo. It'll show up prominently when recruiters visit your profile.

---

## 🆘 Troubleshooting

**Error: "Permission denied (publickey)"**
- Solution: Set up SSH keys → [GitHub Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

**Error: "fatal: remote origin already exists"**
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/wireless-validation-pytest.git
```

**Files not showing up:**
- Make sure you did `git add .` before `git commit`
- Check `.gitignore` isn't excluding them

---

## ✅ You're Done!

Your repo is now live at:
```
https://github.com/YOUR_USERNAME/wireless-validation-pytest
```

Share this link on your resume, LinkedIn, and job applications!

---

**Questions?** Create an issue in the repo or reach out via LinkedIn.
