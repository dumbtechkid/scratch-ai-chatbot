# 🤖 Scratch AI Chatbot (24/7 Cloud Connected)

Ever wanted to put a real, intelligent AI chatbot right inside a Scratch project? 

This repository has everything you need to connect any Scratch 3.0 project to a high-speed AI (powered by Groq) that runs **24/7 in the cloud completely for free**. You can ask it math problems, science questions, coding help, or just have a fun conversation—directly from the Scratch stage!

---

## ⚡ How It Actually Works (The Secret Behind It)

If you've ever worked with Scratch Cloud Variables, you already know the big roadblock: **Scratch cloud variables can only store numbers—never letters or words.**

So how do we get Scratch to talk to an AI? We built a two-way numeric bridge:

```
[ You type question ]
         ↓
[ Scratch encodes text → 2-digit numbers (e.g. "hi" → 10809) ]
         ↓
[ Writes numbers to ☁ INPUT ]
         ↓ (Scratch Cloud WebSocket)
[ Python Cloud Server catches the numbers ]
         ↓
[ Python decodes numbers → English question ]
         ↓
[ Sends question to Groq AI (Llama / GPT models in < 1s) ]
         ↓
[ Groq returns the AI answer ]
         ↓
[ Python encodes reply → numbers ]
         ↓
[ Writes numbers to ☁ OUTPUT ]
         ↓ (Scratch Cloud WebSocket)
[ Scratch detects new numbers → decodes back to English ]
         ↓
[ Formats & displays response inside the on-stage chat log! ]
```

All of this happens in about **1 to 2 seconds**!

---

## 🛠️ The Tech Stack

* **[Scratch 3.0](https://scratch.mit.edu)** — Frontend visual project with custom word-wrapped chat list and two-way cloud encoding.
* **[scratchattach](https://github.com/TimMcCool/scratchattach)** — Lightweight Python library created by TimMcCool that connects directly to Scratch's cloud WebSocket servers.
* **[Groq Cloud API](https://console.groq.com)** — Lightning-fast LLM inference providing 14,400 free requests per day.
* **[GitHub Actions](https://github.com/features/actions)** — Free continuous runner that keeps the Python script running 24/7 without needing your computer on.

---

## 🚀 Quick Setup (Choose Your Mode)

### Prerequisites:
1. **A Scratch Account with "Scratcher" Status:** Scratch restricts cloud variables for brand new accounts ("New Scratcher"). You need standard "Scratcher" status.
2. **A Free Groq API Key:** Takes 30 seconds to generate at [console.groq.com/keys](https://console.groq.com/keys) (no credit card needed).

---

### Option 1: 24/7 Free Cloud Hosting (Recommended)
*You don't need to keep your laptop open or terminal running—GitHub runs it for you in the cloud.*

1. **Fork or create your own copy of this repository on GitHub.**
2. Go to your repository's **Settings → Secrets and variables → Actions**.
3. Click **New repository secret** and add each of these 4 secrets:
   * `SCRATCH_USERNAME` — Your Scratch username.
   * `SCRATCH_PASSWORD` — Your Scratch password.
   * `SCRATCH_PROJECT_ID` — The ID from your Scratch project URL (`scratch.mit.edu/projects/123456789/` $\rightarrow$ `123456789`).
   * `GROQ_API_KEY` — Your key from [console.groq.com](https://console.groq.com).
4. Go to the **Actions** tab, click **24-7 Scratch AI Bot** on the left, and click **Run workflow**.
5. That's it! Your bot is now online and listening to your Scratch project 24/7.

---

### Option 2: Run Locally on Your Computer

1. **Clone this repository:**
   ```bash
   git clone https://github.com/dumbtechkid/scratch-ai-chatbot.git
   cd scratch-ai-chatbot
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your credentials:**
   Open `.env` in a text editor and fill in your details:
   ```env
   SCRATCH_USERNAME=your_scratch_username
   SCRATCH_PASSWORD=your_scratch_password
   SCRATCH_PROJECT_ID=your_project_id
   GROQ_API_KEY=gsk_your_groq_key
   GROQ_MODEL=openai/gpt-oss-120b
   ```

4. **Start the bot:**
   ```bash
   python bot.py
   ```
   You should see:
   ```text
   Connected to Scratch project 123456789 as 'your_username'.
   Listening for Scratch cloud events...
   ```

---

## 🎮 Setting Up the Scratch Project

1. Open the [Scratch Editor](https://scratch.mit.edu/projects/editor).
2. Click **File → Load from your computer**.
3. Select `AI Chatbot.sb3` included in this repository.
4. If you created a new project, make sure it has two cloud variables:
   * `☁ INPUT`
   * `☁ OUTPUT`
5. Click the **Green Flag**, type a question in the ask prompt, and watch the AI reply in the chat log!

---

## 🤖 Want an AI Assistant to Set This Up for You?

If you prefer using an AI assistant (like ChatGPT, Claude, Cursor, Copilot, or Antigravity) to handle the setup, simply open the [`LLM.md`](LLM.md) file in this repository and copy-paste it into your AI prompt window. The AI will guide or automate the entire setup process for you!

---

## 💡 Customizing the Bot's Personality

Want your bot to act like a pirate, a friendly tutor, or a game character?

Open `bot.py` and find `SYSTEM_PROMPT`:
```python
SYSTEM_PROMPT = (
    "You are a friendly, intelligent, and helpful AI assistant in a Scratch project. "
    "Speak naturally, normally, and conversationally. "
    "Keep every response strictly under 120 characters and do not use newlines."
)
```
Change this text to whatever personality you want! Just be sure to keep the instruction about keeping responses under 120 characters, since Scratch cloud variables have a 256-digit limit.

---

## ❓ Frequently Asked Questions

**Q: Scratch says "Thinking..." but nothing happens?**
* Double-check that your Scratch account has the full "Scratcher" status (not "New Scratcher"). New accounts cannot write to or receive cloud variables.
* Verify the project ID in your `.env` or GitHub Secrets matches the URL of your project.

**Q: Is Groq really free?**
* Yes! Groq's free tier provides 14,400 requests every single day, which is more than enough for a Scratch project.

**Q: Why do answers have to be under 127 characters?**
* Scratch limits cloud variables to 256 digits. Since each character encodes into 2 digits (plus a 1-digit sentinel header), `(256 - 1) / 2 = 127` characters maximum per message.

---

## 📜 License & Acknowledgments
* Scratch is a project of the Scratch Foundation, in collaboration with the Lifelong Kindergarten Group at the MIT Media Lab.
* Built with `scratchattach` by TimMcCool.
* Open source and free to use for any educational or personal project!
