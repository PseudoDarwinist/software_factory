# MCP Integration Guide – Bring Your Own Assistant 🚀

This short note shows you how to plug **Software-Factory** into any MCP-ready coding assistant (Claude Code, Cursor, etc.).  
The result: the assistant can read idea context, write back `requirements.md`, `design.md`, and `tasks.md`, and you keep full control.

---

## 1. Why bother?

* Product owner drags an idea to **Define**.  
* Your favourite assistant (Copilot, Claude, or others) writes the spec docs.  
* Docs appear in the UI, you press **Freeze Spec**, life goes on.  
No more switching windows or copy-pasting prompts.

---

## 2. What you need

* Python 3.11 and `pip install -r requirements-mcp.txt`  
* Running Software-Factory stack (`docker compose up` is fine)  
* Claude Code (or another MCP client) installed locally

---

## 3. Start the MCP server

From the project root:

```bash
python -m src.mcp.server
```

You should see:

```
Starting Software Factory MCP server
```

This keeps listening on **stdio** (the default transport).

> Tip: run it inside `tmux` or VS Code terminal so it stays up.

---

## 4. Tell Claude Code about the server

In your project folder:

```bash
claude mcp add sf-server -- python -m src.mcp.server
```

That’s it.  Claude stores the entry in `.mcp.json` (project scope).  
Next time Claude opens in this repo it auto-connects.

### Want HTTP instead of stdio?

1. Run the server through `uvicorn`:

   ```bash
   uvicorn src.mcp.http_server:app --port 6060
   ```

2. Register:

   ```bash
   claude mcp add --transport http sf-http http://localhost:6060/mcp
   ```

The stdio version is simplest for local dev; HTTP/SSE works for remote teams.

---

## 5. What tools does the server expose?

* **get_context** – assistant gives `idea_id`, gets JSON with idea text, system-map, repo link.  
* **save_spec** – assistant posts `{idea_id, spec_type, content}` to store markdown.  
* Three helper prompts `generate_requirements`, `generate_design`, `generate_tasks` are also listed for convenience.

Claude discovers these automatically; you don’t need extra config.

---

## 6. End-to-end example

1. You drag “Dark mode support” into **Define**.  
2. In Claude chat type:  
   ```
   /mcp__sf-server__generate_requirements idea_123
   ```  
   Claude calls **get_context**, writes the document, then calls **save_spec**.  
3. Requirements tab lights up in the UI.  
4. Ask Claude:  
   ```
   write the design doc now
   ```  
   Claude calls the second prompt, then **save_spec** again.  
5. When all three docs are saved, **Freeze Spec** activates.  
   Everything else (Planner-Agent, Kanban board) works unchanged.

---

## 7. Safety switch

To disable BYOA at any time:

```bash
claude mcp remove sf-server   # client side
```

or just stop the server process.

No server, no calls, app behaves exactly as before with the built-in Define-Agent.

---

## 8. Troubleshooting

* **Claude says “connection closed”** → server not running or wrong path.
* **Specs don’t show up** → check server log; look for “Failed to save specification”.
* **Need to reset approvals** → `claude mcp reset-project-choices`.

---

You’re done! Your Software-Factory instance can now collaborate with any MCP-aware assistant you or your team prefer. Happy spec-writing. 🎉
