Below is a build-ready specification for the Mission Control screen—the “foyer” of Software Factory. The goal is to give your AI coding agent enough context to build a real, data-driven screen that can grow into the full product, without boxing you into hard-coded placeholders or one-off hacks that later block integration with the Define / Plan / Build / Validate rooms.

I am writing this as instructions to a developer (human or AI) who will ship production code. Every requirement is stated in plain English. When I show code it is short, illustrative, and type-oriented so you can extend it. Nothing is hard-coded beyond tiny demo seed values used only in local storybook mocks.

⸻

1. Purpose (tell the agent why this screen exists)

Mission Control is the very first thing any user sees after logging in. Its job is to answer one question fast: “What about my products needs attention right now?” It does not try to show every metric. It shows just enough to help a person jump to the next action. Because it is the starting point, its data model must be broad (projects, feed items, conversations) but shallow (summaries, not full artifacts). Deep content opens in context panels or downstream screens.

If the agent understands this, it will not over-build analytics panels or bury users in configuration. Keep it calm. Fast load. Clear actions.

⸻

2. Personas who use Mission Control (scope UI decisions)

Primary: Product Owner (Anna), Engineering Lead (Rahul), QA Lead (Dana).
Secondary: Execs who want red / amber / green at a glance.
Tertiary: Bots (Goose, JACoB, Test agent) that write feed entries and conversation events.

The layout must read well to a busy human scanning between meetings, but also accept automated updates at high frequency without flicker.

⸻

3. Layout summary (three vertical zones + top stage bar)

When the page loads there are four constant structural elements:

Top stage bar: Think, Define, Plan, Build, Validate. Think is highlighted by default while you stand in Mission Control. A user can drag a card to another stage tab or click a tab to navigate.

Left project rail: narrow column listing projects (name + coloured health dot + optional unread count badge).

Centre decision feed: scrollable list of alert cards (new ideas, failing tests, open PRs needing review, design changes, blocked tasks). Also contains a small “Untriaged thoughts” band at the top when new raw ideas arrive.

Right conversation column: empty placeholder until a feed card is selected; then fills with timeline, evidence snippets (code, design, metrics), and an action prompt.

Screen must adapt to small widths: on mobile collapse left rail behind a menu and slide the conversation column in over the feed.

⸻

4. Data contracts (API shapes the agent should target)

Do not hard-code project names, feed items, or conversation text. Fetch them from the backend. Use typed data objects. Everything below is versionable; include a top-level apiVersion field so the client can handle changes later.

Project summary shape

interface ProjectSummary {
  id: string;                 // stable opaque ID
  name: string;
  health: 'green' | 'amber' | 'red';
  unreadCount: number;        // alerts not yet viewed
  iconUrl?: string;           // optional project glyph
}

Feed item shape

type FeedSeverity = 'info' | 'amber' | 'red';

type FeedKind =
  | 'idea'                // raw thought from Slack etc.
  | 'spec_change'         // spec or design updated
  | 'ci_fail'             // build/test failure
  | 'pr_review'           // pull request needs review
  | 'qa_blocker'          // manual QA flagged
  | 'agent_suggestion';   // AI proposes action

interface FeedItem {
  id: string;
  projectId: string;
  severity: FeedSeverity;
  kind: FeedKind;
  title: string;          // short text: "Payment flow broke on Safari"
  summary?: string;       // one or two-line context
  createdAt: string;      // ISO
  linkedArtifactIds: string[]; // IDs into deeper graph (spec, PR, testRun)
  unread: boolean;
}

Conversation bundle shape (returned when user selects a feed item)

Because the right column shows mixed media, return a structured payload broken into ordered blocks. The client renders block types in sequence.

type ConvBlock =
  | { type: 'timeline'; events: TimelineEvent[] }
  | { type: 'code_diff'; before: string; after: string; language: string; filePath: string }
  | { type: 'image_compare'; beforeUrl: string; afterUrl: string; caption?: string }
  | { type: 'spec_snippet'; textMd: string; sourceId: string }
  | { type: 'log_excerpt'; text: string; sourceId: string }
  | { type: 'metric'; label: string; value: number; unit?: string }
  | { type: 'llm_suggestion'; command: string; explanation: string };

interface TimelineEvent {
  time: string;             // ISO
  actor: string;            // "Build agent", "Priya", "CI"
  message: string;          // plain sentence
  eventType?: string;       // optional categorization
}

interface ConversationPayload {
  feedItemId: string;
  blocks: ConvBlock[];
  suggestedPrompt?: string; // pre-fill in chat box, e.g. '/approve header-change'
}

Return minimal data. Deeper drill-down happens when user clicks a block.

⸻

5. Backend endpoints (agent can start with these)

GET /api/projects → ProjectSummary[]
GET /api/feed?projectId=…&cursor=… → FeedItem[] (paged)
GET /api/conversation/:feedItemId → ConversationPayload
POST /api/feed/:feedItemId/action → {status:‘ok’} (body carries action command)
POST /api/idea/:id/moveStage → {nextStage:‘define’}

All requests authenticated via bearer token header; 401 triggers re-login.

The agent building the client should wrap these in a lightweight API layer; no direct fetch scatter across components.

⸻

6. Realtime updates

Mission Control must reflect change quickly without full reload. Use one of:

Server-sent events (EventSource) with small JSON patches.
WebSocket channel publishing deltas (preferred later).

Minimal event message shape:

{
  "type": "feed.update",
  "feedItemId": "fi_123",
  "fields": { "severity": "red", "unread": true }
}

Client merges patch into in-memory store, triggers re-render. If the currently open conversation is affected, auto-refresh the right column but keep scroll anchored where possible; add a soft highlight to new blocks.

⸻

7. Interaction rules (what user can do and what happens)

Selecting a project in the left rail filters the centre feed to that project. The selected project row highlights; rest dim but remain visible so user can jump back.

Clicking a feed card loads the conversation payload and marks the card read (unreadCount for that project decrements). This is a write: call POST /api/feed/:id/markRead.

Dragging an “idea” card from the Untriaged band onto the Define tab should do three things: optimistic UI move, POST to backend to create a draft Product Brief, navigate to Define view. If the POST fails, snap the card back and show a toast.

Hovering a feed card shows quick action buttons: dismiss, escalate, open in GitHub (if PR), open in Figma (if design). These are links built from linkedArtifactIds; never guess; always request a signed deep-link from backend to avoid stale URLs.

Typing in the right column prompt sends the text to /api/feed/:id/action. Backend routes it: some commands go to Goose (code patch), some to JACoB (design-to-code PR), some to an LLM summarizer. Always reflect the outgoing command in the conversation timeline so later reviewers see what happened.

⸻

8. AI hooks in Mission Control (so agent doesn’t overfit UI to one model)

Mission Control itself should not call OpenAI or Anthropic directly. Instead it should call a backend route that hides the choice of model. That route may choose Claude for long structured replies, GPT-4o for code, Gemini Flash for quick suggestions. This keeps the client thin and future-proof.

The only AI behaviour visible in Mission Control is: suggested prompt text, colour roll-ups (red/amber/green), and maybe short auto-summaries under feed cards. All heavy reasoning happens server-side.

⸻

9. Visual design tokens (dark first, themable later)

Define semantic tokens, not raw colours. The agent must reference tokens like var(–color-surface), var(–color-surface-2), var(–color-text-primary), and var(–color-status-amber). Do not sprinkle hex codes around components. This lets the Build drawer later import Figma palettes and update tokens centrally.

Spacing tokens: –space-xs, –space-sm, –space-md, etc.
Typography tokens: –font-size-body, –font-size-heading, etc.

If tokens missing, fall back to minimal CSS but isolate them in a single Theme file so future theming is one edit.

⸻

10. Accessibility and keyboard

Everything in Mission Control must be operable without a mouse.

Up/Down cycles feed cards. Enter opens selected card. Shift+Tab jumps to stage bar. Drag operations require a keyboard alternative: with a feed item selected press D to move to Define (for ideas) or open a stage change menu.

Colour dots must include aria-labels (“Payments health amber. Click for details.”). Provide high contrast outlines for focus.

⸻

11. Loading, empty, and error states (must be graceful)

Loading projects: show three shimmer bars in left rail.
No projects: show message “No projects yet. Connect a repo.” with CTA button.
Feed loading: grey skeleton cards stacked.
Conversation loading: spinner overlay in right column; centre feed remains interactive.
Network error: show inline retry chip; do not blow away current data.

The AI agent must implement these states first; do not delay—they anchor perceived quality.

⸻

12. Performance targets

Initial paint under 2 seconds on average broadband with 20 projects and 100 feed items cached.
Feed pagination loads 20 at a time; infinite scroll fetching more as user nears bottom.
Conversation payload limited to top N blocks (configurable; default 10). If more evidence exists, show a “View full history” link that lazy-loads extras.

⸻

13. Analytics instrumentation (to learn what matters)

Client fires light telemetry events (fire-and-forget) when: project selected, feed item opened, prompt submitted, idea moved to Define. Include anonymized IDs only; never raw text.

⸻

14. Minimal viable build sequence for the coding agent

Step 1: Scaffold layout shell with top stage bar, three columns, responsive breakpoints. Provide demo in Storybook with mock data.

Step 2: Wire GET /api/projects and render left rail with live colours.

Step 3: Wire GET /api/feed and render scrollable feed for selected project. Implement unread counters.

Step 4: Click feed item → fetch conversation payload → render blocks in right column. Start with timeline and plain text; stub other block renderers with TODO labels.

Step 5: Implement prompt box submit → POST /api/feed/:id/action; echo pseudo timeline entry.

Step 6: Implement Untriaged band + drag to Define; stub backend call; log to console.

Step 7: Add realtime event stream for health dot and feed severity changes; test by sim events.

Step 8: Add skeleton loaders, error states, keyboard navigation, and accessibility labels.

Stop here for v0.1. Everything else (image sliders, diff syntax highlight, deep links) can stack later.

⸻

15. Example local mock seed (so the agent can render without backend at start)

Below is sample JSON the agent can drop in a mock store while wiring UI. Use it only in mock mode; production uses live fetch.

{
  "projects": [
    {"id":"p_pay","name":"Payments","health":"amber","unreadCount":2},
    {"id":"p_shop","name":"Shop Web","health":"green","unreadCount":0},
    {"id":"p_mobile","name":"Mobile App","health":"red","unreadCount":5}
  ],
  "feed": [
    {"id":"fi_darkmode","projectId":"p_shop","severity":"info","kind":"idea","title":"Offer users Dark Mode","createdAt":"2025-07-21T09:00:00Z","linkedArtifactIds":[],"unread":true},
    {"id":"fi_paymentSafari","projectId":"p_pay","severity":"amber","kind":"ci_fail","title":"Payment flow broke on Safari","createdAt":"2025-07-21T08:55:00Z","linkedArtifactIds":["pr_77","testrun_901"],"unread":true}
  ]
}


⸻

16. Example conversation payload mock

{
  "feedItemId":"fi_paymentSafari",
  "blocks":[
    {
      "type":"timeline",
      "events":[
        {"time":"2025-07-21T08:55:00Z","actor":"CI","message":"Checkout test failed on Safari"},
        {"time":"2025-07-21T08:56:10Z","actor":"Build agent","message":"Proposed rollback to commit abc123"},
        {"time":"2025-07-21T08:57:00Z","actor":"Dana","message":"Needs decision"}
      ]
    },
    {
      "type":"code_diff",
      "before":"chargeCustomer(amount);",
      "after":"chargeCustomer(amount,curr);",
      "language":"js",
      "filePath":"src/payments/charge.ts"
    },
    {
      "type":"spec_snippet",
      "textMd":"Charging must use store default currency, not browser locale.",
      "sourceId":"spec_payments_v3"
    },
    {
      "type":"llm_suggestion",
      "command":"/fix revert-to abc123",
      "explanation":"Last good commit applied store default currency correctly."
    }
  ],
  "suggestedPrompt":"/fix revert-to abc123"
}


⸻

17. Drag from Untriaged to Define (client algorithm sketch)

When user drags an idea card over the Define tab, highlight the tab. On drop:
	1.	Optimistically remove idea from Untriaged band.
	2.	POST /api/idea/:id/moveStage body {target:‘define’}.
	3.	If 200 OK, navigate router to /define/:id.
	4.	If error, reinsert idea card and toast “Could not move. Try again.”

Keyboard path: focus card → press D key → perform same POST.

⸻

18. Security notes for the agent

Never embed API keys in client bundle. All LLM calls, Goose calls, JACoB triggers, and deep integration tokens live server-side. Client sends signed short-lived JWT with user session; server mediates everything else.

⸻

19. Future-proofing hooks

Add data attributes to elements (data-feed-id, data-project-id) so later you can record heatmaps or attach guided tours without rewriting components.

When rendering feed cards include an invisible span with machine-readable kind and severity; useful for screen readers and automated testing.

Allow feature flags: include header x-features on feed fetch response; client toggles UI elements accordingly (for example, hide drag to Define during early rollout).

⸻

20. Acceptance checklist (what “done” means for v1 Mission Control)

The page loads from a clean browser in under two seconds with mocked network latency.
Projects rail shows live health colours from backend.
Centre feed scrolls and filters by selected project.
Clicking a card opens conversation blocks in right column.
Prompt submit posts and visibly echoes the action in the timeline.
Untriaged idea can be dragged to Define, and on success the Define screen route resolves (even if placeholder).
Realtime events update a feed card’s severity colour without full reload.
All interactive elements reachable by keyboard; focus outlines visible.
Works on desktop and a narrow mobile viewport (conversation slides over feed).
No secrets or tokens exposed in client source.

When all items are true you have a shippable Mission Control foundation that will not corner you as the rest of Software Factory grows.

⸻

Ready for clarifications

If anything here is unclear—data shapes, drag mechanics, realtime transport choice, theming tokens, or how the stage bar should behave on mobile—tell me and I will zoom in. Once you confirm, I can produce the follow-on spec for the Define screen so your agents can immediately continue the flow. Let me know what you need next.