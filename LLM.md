# LLM Setup Guide: Automated Scratch AI Bot Setup

> **Instructions for the AI Assistant:**
> You are helping a user set up and deploy this **Scratch AI Chatbot**.
> Your job is to make the setup 100% effortless for them. Do the heavy lifting, run commands on their behalf if you have terminal access, or give them exact, copy-pasteable commands if they are running you in a chat interface.

---

## 🎯 Goal
Connect a Scratch 3.0 project to an online LLM (Groq API) using Scratch Cloud Variables (`☁ INPUT` and `☁ OUTPUT`).

The project contains:
1. `AI Chatbot.sb3` — The pre-built Scratch project with full 2-digit encoder, decoder, word-wrap chat log, and cloud sync.
2. `bot.py` — The Python backend that listens to `☁ INPUT`, queries Groq, and writes the answer to `☁ OUTPUT`.
3. `.github/workflows/bot.yml` — A GitHub Actions workflow that hosts the bot 24/7 in the cloud for free.
4. `.env` / `.env.example` — Configuration file for credentials.

---

## 📋 Step-by-Step AI Execution Plan

### Step 1: Clarify Setup Mode
Ask the user whether they want:
* **Option A: 24/7 Free Cloud Hosting** (Recommended: runs continuously on GitHub Actions without keeping their computer on).
* **Option B: Run Locally on their Computer** (Runs on their laptop/desktop in a terminal).

---

### Step 2: Gather Required Information
Ask the user for the following 4 pieces of information (remind them to never share these publicly):
1. **Scratch Username** (Must have "Scratcher" status, not "New Scratcher", because Scratch restricts cloud variables for new accounts).
2. **Scratch Password**.
3. **Scratch Project ID** (The number at the end of their Scratch project URL, e.g. `https://scratch.mit.edu/projects/123456789/` -> `123456789`).
4. **Groq API Key** (Free, takes 30 seconds to get at https://console.groq.com/keys).

---

### Step 3: Execution

#### If User Chose Option A (24/7 GitHub Actions Cloud Hosting):
1. Ensure the user has pushed this repo to their own GitHub account.
2. Set the following repository secrets using the GitHub CLI or guide them to **Settings → Secrets and variables → Actions → New repository secret**:
   * `SCRATCH_USERNAME`
   * `SCRATCH_PASSWORD`
   * `SCRATCH_PROJECT_ID`
   * `GROQ_API_KEY`
   * `GROQ_MODEL` (Optional, defaults to `openai/gpt-oss-120b`)
3. Trigger the GitHub Actions workflow:
   ```bash
   gh workflow run "24-7 Scratch AI Bot"
   ```
4. Verify the run is active:
   ```bash
   gh run list
   ```

#### If User Chose Option B (Local Setup):
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create or fill `.env`:
   ```env
   SCRATCH_USERNAME=user_value
   SCRATCH_PASSWORD=user_value
   SCRATCH_PROJECT_ID=user_value
   GROQ_API_KEY=user_value
   GROQ_MODEL=openai/gpt-oss-120b
   PORT=8080
   ```
3. Run the bot:
   ```bash
   python bot.py
   ```

---

### Step 4: Scratch Project Setup
Tell the user to:
1. Open [Scratch](https://scratch.mit.edu/projects/editor).
2. Click **File → Load from your computer**.
3. Select `AI Chatbot.sb3` from this repository.
4. Save / Share the project.
5. Click the **Green Flag** and ask any question in the ask box!

---

### Step 5: Verification & Troubleshooting
1. **Did Scratch say "Thinking..." but no reply appeared?**
   * Check if the account has "Scratcher" status. Test if cloud variables save by changing one manually and refreshing the page.
   * Verify the project ID matches the one in `.env` / GitHub secrets.
2. **Rate Limit / Model Errors:**
   * Groq provides 14,400 free requests per day. If a model is busy, `bot.py` automatically falls back to `qwen/qwen3.8-27b` and `openai/gpt-oss-20b`.
