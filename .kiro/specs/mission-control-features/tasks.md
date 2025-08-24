# Implementation Plan - MVP-Driven Development

## 🎯 MVP 1: Plan Stage Foundation (Tasks 1-6)

_Goal: Complete Plan stage with task management, agent selection, and GitHub integration_

**Testable Outcome**: User can see tasks, select agents, configure context, and connect to GitHub

- [x] 1. Plan stage UI foundation (Task 11 - Basic Implementation)

  - **Goal**: Kanban view with task cards, status columns, and basic interaction
  - **Do**: Create Ready/In Progress/Done columns, task cards with title/owner/effort, Start button opens side panel
  - **Test**: User can see tasks, click Start, see side panel with agent dropdown
  - _Requirements: 4, 10_
  - _Completion: Basic Plan stage renders with task data_

- [x] 2. Task execution API (Task 10)

  - **Goal**: Backend endpoints for task lifecycle management
  - **Do**: POST /api/tasks/:id/start, WebSocket progress stream, context/retry/cancel endpoints
  - **Test**: API can start tasks, stream progress, handle retries
  - _Requirements: 4, 5_
  - _Completion: Frontend can start/watch/retry tasks via API_

- [x] 3. Plan cards with intelligent signals (Task 11.1)

  - **Goal**: Cards show priority, assignee suggestions, effort estimates
  - **Do**: Add editable priority/status/assignee fields, "Suggest" buttons, goal line from acceptance criteria
  - **Test**: Cards show real data, Suggest buttons work, user can override suggestions
  - _Requirements: 18.1, 18.2_
  - _Completion: Cards display planning intelligence, not hard-coded data_

- [x] 4. Agent run panel with context options (Task 11.2)

  - **Goal**: Complete side panel for agent selection and configuration
  - **Do**: Agent selection (Claude Code/AI Garden/Kiro), context checkboxes, branch naming, preflight status
  - **Test**: Panel shows all options, validates GitHub connection, generates branch names
  - _Requirements: 18.4, 18.5_
  - _Completion: Panel ready for actual agent execution_

- [x] 5. GitHub integration and preflight checks (Tasks 11.7, 11.8)

  - **Goal**: Connect projects to GitHub repositories with validation
  - **Do**: Project settings for repo URL/token, preflight validation, connection status display
  - **Test**: Projects show "GitHub connected" status, preflight catches issues
  - _Requirements: 17.1, 5_
  - _Completion: Reliable GitHub connectivity before agent runs_

- [x] 6. Branch naming and collision handling (Task 11.4)
  - **Goal**: Consistent, conflict-free branch names
  - **Do**: Generate feature/bug/hotfix branches with collision detection
  - **Test**: Branch names never collide, user can edit suggested names
  - _Requirements: 17.1_
  - _Completion: Every task gets a unique, valid branch name_

## 🎯 MVP 2: Agent Execution Core (Tasks 7-12)

_Goal: Agents actually execute with Claude Code SDK and create real branches/PRs_

**Testable Outcome**: Click "Start Task" → See Claude Code create branch → Make changes → Open PR

- [x] 7. Local clone and branch creation (Task 11.9)

  - **Goal**: Give Claude Code a real working copy for each task
  - **Do**: Shallow-clone repo into task-specific folder, create/push branch before agent starts
  - **Test**: New branch exists in GitHub repo before agent execution
  - _Requirements: 5_
  - _Completion: Git workspace ready for Claude Code SDK_

- [x] 8. Claude Code sub-agent execution (Task 11.21)

  - **Goal**: Actually invoke Claude Code SDK with selected sub-agent
  - **Do**: Use `claude -p "Use the feature-builder sub agent..."` with .claude/agents/ detection
  - **Test**: Selected agent runs with proper context, makes real code changes
  - _Requirements: 16.3, 16.5_
  - _Completion: Agent selection in UI controls actual Claude Code sub-agent used_

- [x] 9. Sub-agent choices and auto-routing (Tasks 11.5, 11.6)

  - **Goal**: Proper sub-agent selection with intelligent defaults
  - **Do**: Show feature-builder/test-runner/code-reviewer/debugger/design-to-code options, auto-route by task type
  - **Test**: Different agents produce different results, auto-routing suggests correct agent
  - _Requirements: 16.1, 16.2_
  - _Completion: Agent selection is intelligent and affects execution behavior_

- [x] 10. Pull request creation and linking (Task 11.10)

  - **Goal**: Every successful run produces a reviewable PR
  - **Do**: Push branch, create draft PR, link back to task, flip to ready when tests pass
  - **Test**: Task completion shows working PR link immediately
  - _Requirements: 5_
  - _Completion: End-to-end task → PR workflow working_

- [x] 11. Progress tracking and live updates (Task 11.13)

  - **Goal**: Real-time progress from agent execution
  - **Do**: Stream progress from Claude Code execution, update UI in real-time
  - **Test**: User sees smooth progress sequence during agent execution
  - _Requirements: 5_
  - _Completion: Live progress updates during agent runs_

- [x] 12. Error handling and retry (Task 11.17)
  - **Goal**: Graceful failure recovery
  - **Do**: Failed tasks show clear errors, retry with previous settings, cancel running tasks
  - **Test**: Failed task can be retried successfully, running tasks can be cancelled
  - _Requirements: 5_
  - _Completion: Robust error handling and recovery_

## 🎯 MVP 3: Build Stage Integration (Tasks 13-18)

_Goal: Complete Build stage with PR management and GitHub webhooks_

**Testable Outcome**: Tasks move to Build stage → Show PR status → Merge updates task status

- [x] 13. Build stage dashboard (Task 11.23)

  - **Goal**: Central place to watch running tasks and manage PRs
  - **Do**: List Running/Review/Failed tasks, show live logs, PR diffs, failure excerpts
  - **Test**: Can watch task progress, open PRs, see detailed execution logs
  - _Requirements: 5_
  - _Completion: Build stage provides comprehensive task monitoring_

- [x] 14. GitHub webhooks integration (Task 11.11)

  - **Goal**: Automatic task status updates from GitHub events
  - **Do**: Webhook endpoint for PR events, update task status on merge/close
  - **Test**: Merging PR automatically marks task Done in real-time
  - _Requirements: 5_
  - _Completion: GitHub events drive task status changes_

- [ ] 15. Task approval and resolution (Task 11.24)

  - **Goal**: Complete task lifecycle management
  - **Do**: Approve/Retry/Send back buttons, PR linking, task resolution
  - **Test**: Reviewer can resolve tasks without leaving Build stage
  - _Requirements: 5_
  - _Completion: Full task resolution workflow_

- [ ] 16. Context bundling and optimization (Task 11.14)

  - **Goal**: Efficient context delivery to agents
  - **Do**: Assemble checked context files, optimize for agent consumption
  - **Test**: Agent receives exactly what user selected in context options
  - _Requirements: 5_
  - _Completion: Context options directly control agent input_

- [ ] 17. Test execution and reporting (Task 11.16)

  - **Goal**: Real test outcomes visible in UI
  - **Do**: Run tests during agent execution, capture results, show pass/fail status
  - **Test**: Build stage shows clear test results and failure details
  - _Requirements: 5_
  - _Completion: Test results integrated into task workflow_

- [ ] 18. Concurrency and resource management (Task 11.19)
  - **Goal**: Prevent system overload and conflicts
  - **Do**: Task execution limits, queueing system, conflict detection
  - **Test**: Multiple tasks run without conflicts, queue position visible
  - _Requirements: 5_
  - _Completion: Reliable multi-task execution_

## 🎯 MVP 4: Advanced Agent Features (Tasks 19-24)

_Goal: Sub-agent chaining, intelligent suggestions, and optimization_

**Testable Outcome**: Agents suggest better defaults → Chain automatically → Provide performance insights

- [ ] 19. Plan-mode suggestions with Claude Code (Task 11.3)

  - **Goal**: Intelligent planning assistance without code changes
  - **Do**: Claude Code in read-only mode for assignee/estimate/path suggestions
  - **Test**: Suggest buttons provide intelligent defaults with reasoning
  - _Requirements: 13.1, 13.2, 13.3_
  - _Completion: Planning becomes AI-assisted but human-controlled_

- [ ] 20. Sub-agent detection and validation (Task 11.30)

  - **Goal**: Verify and display available sub-agents per project
  - **Do**: Check .claude/agents/ directory, validate expected files, show status
  - **Test**: Project settings show "Sub agents: 5/5 available" or fallback warning
  - _Requirements: 20.1, 20.2, 20.3_
  - _Completion: Clear visibility into sub-agent availability_

- [ ] 21. Chained sub-agent execution (Task 11.22)

  - **Goal**: Automated agent sequences for quality workflows
  - **Do**: feature-builder → test-runner → code-reviewer chains, debugger on failures
  - **Test**: Single task triggers multiple agents in sequence automatically
  - _Requirements: 16.5, 19.1_
  - _Completion: Automated quality pipeline through agent chaining_

- [ ] 22. Bug tracking and fast-track fixes (Tasks 11.25, 11.26)

  - **Goal**: Failed PRs become trackable bugs with quick fix workflow
  - **Do**: CI failures create bug cards, fast-track fix flow reuses branches
  - **Test**: Red PR creates bug card, fix can be started immediately
  - _Requirements: 5_
  - _Completion: Seamless bug creation and resolution workflow_

- [ ] 23. Performance metrics and telemetry (Tasks 11.35, 11.36)

  - **Goal**: Insights into agent effectiveness and performance
  - **Do**: Track start-to-PR time, model turns, sub-agent performance comparison
  - **Test**: Dashboard shows agent performance metrics and comparisons
  - _Requirements: 20.4, 20.5, 5_
  - _Completion: Data-driven insights into development workflow_

- [ ] 24. System reliability and guardrails (Tasks 11.33, 11.20, 11.32)
  - **Goal**: Production-ready reliability and safety
  - **Do**: Timeouts, idempotency, log retention, duplicate start handling
  - **Test**: System handles edge cases gracefully, maintains audit trail
  - _Requirements: 5_
  - _Completion: Production-ready reliability and observability_

## 🎯 MVP 5: Polish and Production (Tasks 25-30)

_Goal: Demo-ready system with proper UX and accessibility_

**Testable Outcome**: System ready for demo with smooth UX and comprehensive features

- [ ] 25. Demo data and happy path (Task 11.37)

  - **Goal**: Smooth demo experience out of the box
  - **Do**: Sample project setup, demo script, seed data for immediate testing
  - **Test**: Can set up and run full demo in under 5 minutes
  - _Requirements: 1_
  - _Completion: Demo-ready system with sample data_

- [ ] 26. User experience polish (Tasks 11.42, 11.43, 11.44)

  - **Goal**: Professional UX with accessibility and theming
  - **Do**: Microcopy, keyboard navigation, dark theme consistency
  - **Test**: First-time users understand interface, fully keyboard accessible
  - _Requirements: 1_
  - _Completion: Professional, accessible user interface_

- [ ] 27. Debugging and observability (Task 11.38)

  - **Goal**: Easy troubleshooting and bug reporting
  - **Do**: Run correlation IDs, event stream export, detailed logging
  - **Test**: Can export full run transcript for debugging
  - _Requirements: 5_
  - _Completion: Comprehensive debugging and observability_

- [ ] 28. Configuration and customization (Task 11.29)

  - **Goal**: Flexible system configuration per project
  - **Do**: Model defaults, tool permissions, security settings
  - **Test**: Projects work with minimal configuration, can be customized
  - _Requirements: 5_
  - _Completion: Flexible, secure configuration system_

- [ ] 29. Feature flags and advanced features (Task 11.34)

  - **Goal**: Advanced features behind flags for stability
  - **Do**: Feature flags for experimental functionality
  - **Test**: Can enable/disable advanced features without breaking core workflow
  - _Requirements: 5_
  - _Completion: Stable core with optional advanced features_

- [ ] 30. End-to-end validation (Tasks 11.39, 11.40, 11.41)
  - **Goal**: Prove complete workflow reliability
  - **Do**: Start→PR→Merge flow, failure→retry→success flow, real-time updates
  - **Test**: Complete workflows work reliably end-to-end
  - _Requirements: 5_
  - _Completion: Fully validated, production-ready system_

---

## 📋 **Current Status Summary**

### ✅ **Completed (MVP 1 + partial MVP 2)**

- Plan stage UI foundation with task cards and agent selection
- Task execution API with progress streaming
- GitHub integration with preflight checks
- Local Git workspace creation and branch management
- Claude Code sub-agent execution (basic implementation)

### 🚧 **Next Priority (Complete MVP 2)**

- Sub-agent choices and intelligent auto-routing (Task 9)
- Pull request creation and linking (Task 10)
- Real-time progress tracking (Task 11)
- Error handling and retry mechanisms (Task 12)

### 🎯 **MVP Milestones**

- **MVP 1**: ✅ Plan stage foundation (6/6 tasks complete)
- **MVP 2**: 🚧 Agent execution core (2/6 tasks complete)
- **MVP 3**: ⏳ Build stage integration (0/6 tasks)
- **MVP 4**: ⏳ Advanced agent features (0/6 tasks)
- **MVP 5**: ⏳ Polish and production (0/6 tasks)

This reorganization provides clear MVP phases where each phase delivers a testable, working system that builds on the previous phase. You can now work through MVP 2 to get a complete working agent execution system before moving to Build stage integration.
