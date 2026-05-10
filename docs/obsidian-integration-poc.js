/*
 * RuWritingStyles Obsidian Integration (Proof of Concept)
 * This script demonstrates how to connect Obsidian to the RuWritingStyles API.
 * Requirement: The RuWritingStyles API must be running (python src/ruwritingstyles/api.py).
 */

const API_URL = "http://localhost:8000/api/audit/selection";

module.exports = async (params) => {
    const { app, editor } = params;
    const selection = editor.getSelection();

    if (!selection) {
        new Notice("Please select a paragraph to audit.");
        return;
    }

    new Notice("Initiating Socratic Audit...");

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: selection,
                provider: "google", // or "anthropic"
                profile: "researcher"
            })
        });

        const data = await response.json();
        
        if (data.revised) {
            // Show a simple confirmation dialog (Custom Modal suggested for production)
            const confirmReplace = confirm(
                `RuWritingStyles Audit Complete.\n\n` +
                `Findings: ${data.findings.length} points identified.\n\n` +
                `Revised Text:\n${data.revised}\n\n` +
                `Replace selection with revised text?`
            );

            if (confirmReplace) {
                editor.replaceSelection(data.revised);
                new Notice("Selection updated with philological grounding.");
            }
        } else {
            new Notice("Audit failed: " + JSON.stringify(data));
        }

    } catch (err) {
        new Notice("Error connecting to RuWritingStyles API: " + err.message);
    }
};
