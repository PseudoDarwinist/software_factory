Below is a **single-file specification** you can drop straight into your Define-agent prompt, a Notion doc, or a `spec.md` in the repo.
It describes every screen, component, state, and interaction we have discussed—matching the event-driven, agent-powered architecture now in place—but written so a front-end team can implement without guessing.

---

```markdown
# Software Factory — Mission-Control UI Specification

_version 1.0 · 2025-07-22 · living document_

## 0. Visual language

- Dark “mission-control” palette: #0E0F11 background, #1B1C1F panels, #00FFB0 accent on success, #FF5F5F on failure.
- Glass-morphism cards: 8 px blur, 2 px #333 border, 12 px corner radius.
- Typeface: Inter; weights 400 / 600.
- Grid: 12-column, 16 px gutter, 32 px outer margin; breakpoints 1440 / 1024 / 768 / 480.
- Motion: spring-based; 200 ms enter, 120 ms exit; cards “float” 2 px on hover.

## 1. Global layout
```

┌───────────────────────────────────────────────────────────────┐
│ 1 Top Nav │ Project switcher ▾ │ Think > Define > Plan … ○● │
├───────────┬───────────────────────────────┬───────────────────┤
│ 2 Left │ 3 Centre (Feed / Boards) │ 4 Right Panel │
│ Project │ │ Context / Chat │
│ Rail │ │ │
└───────────┴───────────────────────────────┴───────────────────┘

````
*Left rail collapsible (64 → 280 px). Centre flex-fills. Right panel 32 % width, hides on ≤768 px.*

## 2. Project Rail (component `ProjectRail`)
### Data
```ts
interface ProjectSummary {
  id: string;          // uuid
  name: string;        // “Travel Disruption”
  description: string; // one-liner
  health: "green"|"amber"|"red";
  unread: number;      // count of unread feed items
}
````

### Behaviour

- Real-time updates via WebSocket `project.health.changed`.
- Click selects currentProject and pushes route `/p/:projectId/think`.
- “＋ Add Project” opens modal with Git repo URL, Slack channel map, doc upload.
- Dot health animation: pulse 1.5 s when state flips.

## 3. Top Nav (component `StageNav`)

Stages: **Think · Define · Plan · Build · Validate · User · Learn**

- Stage is a route param `/p/:id/:stage`.
- Disabled stages greyed until previous stage has ≥1 item.
- Shows live health dot (green/amber/red) per stage via `stage.health.changed`.

## 4. Think Stage — Feed View (route `/p/:id/think`)

### Centre column (`FeedList`)

Sections auto-bucket by severity:

- **Untriaged thoughts** (grey)
- **Needs attention** (red/amber)
- **FYI** (blue)

Card (`FeedCard`) props:

```ts
{
  id, icon, title, subtitle, severity, createdAt,
  cta?: { label, action },  // e.g. “Drag to Define ➜”
}
```

- Drag-over hint: left border glows stage colour.
- “Dismiss” hides locally, “Escalate” sets severity=high.

### Right panel (`ContextPanel`)

- Empty state: logo bubble + “Ready to help”.
- On select: shows card JSON pretty-printed, raw Slack link, related git commits (graph query).

## 5. Drag to Define interaction

- DnD wrapper emits `idea.promoted` WebSocket → Redis → event bus.
- Optimistic UI instant; backend confirms with `idea.promoted.ack`.
- On mobile (≤768 px) long-press brings bottom sheet of stages.

## 6. Define Stage — Product Brief Editor (`/define`)

### Layout

- Left sub-rail: list of ideas now in Define (column-style).
- Centre: **Product Brief Editor** tabs:

  - **requirements.md** (markdown editor with live preview)
  - **design.md** (rich-text + embedded Figma image slider)
  - **tasks.md** (checkbox list)

- Right panel: AI chat (“Ask Build-AI”) seeded with context.

### Behaviour

- On first load the Define agent fills all three docs, fields marked 🟡 “AI-draft”.
- User edits turn badge 🟢 “Human”.
- **Freeze Spec** button enabled when all required “Human” fields present.
- Clicking Freeze emits `spec.frozen`.

## 7. Plan Stage — Board (`/plan`)

- Board lanes: **Ready · In Progress · Done**.
- Task card props:

```ts
{
  id, title, ownerAvatar, storyPoints, status, branch;
}
```

- Drag to In Progress emits `task.started`.
- Expand card opens drawer with:

  - Claude-Code patch preview.
  - Figma palette snippet.
  - Link to branch diff.

## 8. Build Stage — PR Monitor (`/build`)

- Table rows streamed from GitHub webhook `pr.opened`.
- Columns: PR #, task, author, checks, merge button.
- PR row turns red if Build agent emits `build.failed`.

## 9. Validate Stage — Test Run Viewer (`/validate`)

- Timeline of CI runs; click shows logs, screenshots, AI summary.

## 10. User Stage — Simulation (`/user`)

- Grid of synthetic user sessions: status, persona, friction notet the s.
- “Replay” opens screencast.

## 11. Learn Stage — Insights (`/learn`)

- Card carousel of learn reports.
- “Open as idea” button clones insight into Think stage.

## 12. Real-time data flow

```
Slack → Flask Ingress → Redis.publish(idea.captured) →
WebSocket push to UI + CaptureAgent →
DefineAgent → Redis.publish(spec.frozen) →
PlannerAgent → Redis.publish(tasks.created) →
WebSocket update → BuildAgent …
```

Every stage edit or AI action is a Redis event followed by a WebSocket push.

## 13. API endpoints (front-end uses)

GET `/api/project/:id/summary`
GET `/api/project/:id/feed?stage=think`
POST `/api/idea/:id/move-stage`
POST `/api/spec/:id/freeze`
POST `/api/task/:id/start`
WebSocket `/ws?project=:id` — receives `{type, payload}` events.

## 14. Accessibility

- WCAG 2.1 AA colour contrast.
- Keyboard drag: space picks card, arrow moves, space drops.
- Live-region ARIA updates for new feed cards.

## 15. Performance target

- WebSocket round-trip UI update < 150 ms on LAN.
- Board drag re-render ≤ 8 ms frame budget (RAF batching).
- Initial bundle ≤ 180 kB gzipped; ship icons via sprite.

## 16. Extensibility notes

- Add a new agent → emit new event type → UI listens via same WebSocket.
- To embed Notion: iframe viewer in ContextPanel if URL host `notion.so`.
- To switch Claude-Code for Gemini → update AI Broker; UI untouched.

---

---

## Business-Logic Specification — “Why the app behaves the way it does”

This is the companion to the UI spec. It tells any engineer or product manager exactly **how** and **why** the back-end moves data the way it does, so they can implement or audit the rules without digging through code.

---

### 1 . Project onboarding — giving the platform its context

**Why we add a GitHub repo**
The moment a new project is created we need a concrete, inspectable source of truth for code. Cloning the repo lets the platform:

- scan directories and languages,
- read existing unit tests,
- map service names and event enums,
- tag future commits to tasks automatically.

**Onboarding wizard steps**

1. **Connect repository** — user pastes HTTPS/SSH URL.
   The back-end performs a shallow clone in a temp dir, hashes the commit, and stores a first “system map” row (file tree, language breakdown).
2. **Upload reference docs** — drag in PDFs or Markdown (BRDs, policy docs).
   Each file is chunk-split, embedded (pgvector) and tied to the project.
3. **Link communications** — choose Slack channel(s).
   The channel-to-project map is stored so Capture can tag inbound messages.

At the end of the wizard the project already knows what it is, where its code lives, and what documentation governs it. From then on every inbound idea carries that context.

---

### 2 . Idea flow — from chat to shipped code

1. **Seed event**
   Someone types in the mapped Slack channel. The Slack adapter posts the JSON to `/api/ingress/slack`. That route validates the token then calls
   `publish("idea.received", {text, channel, user, ts})`.

2. **Capture & enrichment**
   Capture agent subscribes to `idea.received`. It:

   - looks up the channel → project ID,
   - checks the system map for keywords (e.g. “gate-change” vs existing `EventType`),
   - passes the text and map to Claude for quick entity tagging,
   - writes a new Idea row and fires `idea.captured`.

3. **Mission Control UI**
   WebSocket bridge forwards `idea.captured` to the browser; the grey card appears in Think.

4. **Define step**
   Dragging to Define calls `/move-stage`; Flask publishes `idea.promoted`.
   Define agent wakes:

   - pulls embeddings for similar specs, the GDPR PDF, and the SMS template,
   - prompts Claude with those snippets,
   - writes `requirements.md`, `design.md`, `tasks.md`,
   - publishes `spec.frozen`.

5. **Planner step**
   Planner agent hears `spec.frozen`.
   It parses `tasks.md`, expands each checkbox into a Task row, pre-fills suggested owner from Git blame history, and publishes `tasks.created`.

6. **Developer picks a task**
   Drag to “In Progress” triggers `task.started`.
   Build agent clones the repo to a scratch dir, pulls context via pgvector (relevant commits, style guides), calls Claude-Code with that context, runs tests locally.
   If tests pass it pushes a branch and opens a PR via GitHub API, then publishes `build.started`.

7. **CI / tests**
   GitHub notifies your CI system. Success → `build.succeeded`; failure → `build.failed`. Test agent may add extra AI-generated tests if the diff touches uncovered code.

8. **Validate, User, Learn**
   After merged, Test agent runs simulations in a staging env and pushes a video + results to the `user.pass` or `user.friction` event.
   Nightly Learn agent walks the event log, computes cycle time, failure rate, and surfaces insights back to Think as new ideas.

---

### 3 . Event rules that keep the factory safe

- **Idempotency** — every event envelope carries `id`. A service must check “have I processed this id?” before acting.
- **Loop guard** — Agent Manager prevents `A → B → A` spirals by storing a sliding window of `(producer, consumer, idea_id)` paths; duplicates within 60 s are dropped.
- **Rate limits** — each agent has `max_events_per_minute`, set via ENV. Exceeding it pauses the agent for a cool-down and publishes `agent.throttled`.

---

### 4 . Data stores and what lives where

- **Postgres** — projects, ideas, specs, tasks, commits, events (append-only).
- **pgvector** — embeddings of every doc chunk, code chunk, commit message.
- **Graph extension** — edges: idea↔spec, spec↔task, task↔commit, commit↔test.
- **Redis** — ephemeral message bus; cleared on restart, no data loss because every event is in Postgres.
- **Object store** (later) — video replays, Figma diffs.

---

### 5 . Security and roles

- **Bearer token** in every WebSocket and REST call encodes `user_id` and `project_ids`.
- WebSocket bridge filters outgoing events: only messages whose `project_id` is in the token are sent.
- Build agent uses short-lived GitHub OAuth tokens issued per task; never stores long credentials.

---

### 6 . Error paths

- If an agent raises an exception it publishes `event.failed` with the original event’s `id` and reason. UI shows a red toast, ops can replay from the event page.
- If Redis is down, Flask writes events to `lost_events` table and serves UI with a banner “real-time channel unavailable.” On recovery a job replays.

---

### 7 . Why the business cares

- **Traceability** — every tiny action, human or AI, is a timestamped event tied back to the originating Slack line. Perfect audit trail.
- **Speed with safety** — AI writes specs and code, but only after context retrieval; tests and user-simulation gates catch regressions.
- **Scalability** — add ten more agents (security scan, cost estimate) without touching existing code; they just subscribe to the bus.
- **Zero tool sprawl** — Slack for chat, GitHub for code, everything else happens in one Mission Control window that updates in real time.

---

This narrative covers the **business logic** from first message to production code, explains why GitHub repo linking matters, and documents all the invisible guard-rails. Feed it to any new collaborator and they know how the system moves, why, and where to hook new capabilities.
