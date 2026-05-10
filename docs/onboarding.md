# Welcome to RuWritingStyles! 🚀

Hello! You are about to use a "Scientific Super-Brain" for your writing. Imagine having a team of the world’s best professors (like Zaliznyak or Bakhtin) sitting next to you, checking every word you write. That is what this project does!

---

## 🏗️ Step 1: Setting up your Workshop
Before the professors can help you, we need to set up their "office."

1. **Install the tools**: Open your terminal (Command Prompt) and run:
   ```bash
   pip install -e .
   ```
   *Example: It’s like installing a new game on your computer. Just wait for the progress bars to finish!*

2. **Give them "Magic Keys"**: Create a file named `.env` and put your AI keys inside:
   ```env
   GOOGLE_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ```
   *Example: Think of these as batteries. Without them, the AI professors won't wake up.*

---

## 🌐 Step 2: Open the Web Studio
The easiest way to work is using the **Web Studio**. It looks like a futuristic dashboard.

1. **Start the engine**:
   ```bash
   rws web
   ```
2. **Open your browser**: Go to `http://localhost:5173`.
3. **What to do**:
   - Click **"+ New Philological Audit"**.
   - Type the path to your file (e.g., `C:\MyDocuments\article.md`).
   - Click **Execute**.

*Example: You will see a "Thinking Trace" on the right. It shows the AI professors talking to each other. "I think this word is too modern," says one. "Let me check the Zotero library," says another.*

---

## ⌨️ Step 3: Use it in your Favorite Editor
You don't even have to leave your writing app!

### For Obsidian:
1. Select a paragraph you just wrote.
2. Run the RWS script (see `docs/obsidian-integration-poc.js`).
3. **Boom!** The professors rewrite it for you instantly.

### For MS Word:
1. Open the **RuWritingStyles Task Pane**.
2. Select your text.
3. Click **"Audit Selection"**.
4. If you like the result, click **"Apply Revision"**.

---

## 🎨 Step 4: Real-World Examples

### Example A: The "Pseudo-Science" check
*   **You write**: "The word 'History' comes from 'His Story', obviously."
*   **The AI Council says**: "Wait! This is folk etymology. The word actually comes from the Greek 'historia' (inquiry)."
*   **The Result**: "The term 'history' derives from the Greek *historia*..."

### Example B: The "Academic Tone" check
*   **You write**: "Zaliznyak was a really cool guy and knew everything about old letters."
*   **The AI Council says**: "Too informal! Let's make it more scholarly."
*   **The Result**: "A. A. Zaliznyak’s contribution to the study of Old Novgorod dialect remains foundational..."

---

## 🧠 Step 5: Socratic Injection (The Superpower)
If the AI is moving in the wrong direction, you can **shout** at it!

1. In the Web Studio, look at the **Thinking Trace**.
2. Type in the box: *"Actually, check the 2014 edition of his book, he changed his mind there."*
3. **The AI will respond**: "Ah, the researcher is right! Changing my deliberation now..."

---

## 🛠️ Summary Checklist
- [ ] **I have Python installed.**
- [ ] **I have my API keys in `.env`.**
- [ ] **I ran `rws web` to see the dashboard.**
- [ ] **I tried selecting text in Obsidian/Word.**

**Happy Scholarly Writing!** If you get stuck, check the `docs/` folder or just ask the AI! 🎓✍️
