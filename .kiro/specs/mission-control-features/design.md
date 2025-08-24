# Design Document

## Overview

The Mission Control Features design implements a sophisticated agent-driven workflow system that transforms the Software Factory into an intelligent development platform. The design centers around seven specialized agents that react to domain events, use context-aware AI, and maintain project state through a unified event-driven architecture.

The system leverages the existing Flask application, PostgreSQL with pgvector and graph extensions, Redis message queue, and WebSocket infrastructure to create seamless automation that feels magical to users while maintaining full transparency and human control.

## Architecture

### High-Level System Flow

```
Slack Message → Capture Agent → idea.captured → WebSocket → Think Stage UI
     ↓
User Drag → idea.promoted → Define Agent → pgvector context → Claude → spec.frozen
     ↓
Planner Agent → tasks.created → Plan Stage UI → User Drag → task.started
     ↓
Build Agent → pgvector context → Claude-Code → PR created → build.started
     ↓
GitHub Webhook → build.succeeded → Test Agent → quality analysis → user.ready
     ↓
User Simulation Agent → synthetic testing → user.friction → Learn Agent
     ↓
Learn Agent → insights generated → pattern.identified → new ideas
```

### Event-Driven Agent Coordination

The system uses a hub-and-spoke model where Redis serves as the central event bus, with each agent subscribing to specific event types and publishing new events based on their processing results. The Agent Manager prevents infinite loops and manages agent lifecycle.

### Context-Aware AI Integration

All AI interactions follow a consistent pattern:
1. Receive domain event with project context
2. Query pgvector for similar historical examples
3. Query graph database for related project artifacts
4. Combine context into structured prompt
5. Call appropriate AI model (Claude, Goose, Gemini)
6. Process response and emit result events

## Components and Interfaces

### 0. Project Onboarding Wizard (`OnboardingWizard.tsx`)

**Three-Screen Flow:**
1. **Connect Repository Screen** - User pastes GitHub HTTPS/SSH URL, system performs shallow clone and generates initial system map
2. **Upload Documentation Screen** - Drag-and-drop interface for PDFs and Markdown files, automatic chunking and pgvector embedding
3. **Link Communications Screen** - Slack channel selection with project mapping, optional webhook configuration for other tools

### 1. Agent Framework (`src/agents/`)

#### Base Agent Class (`base.py`)
```python
class BaseAgent:
    def __init__(self, agent_id: str, event_types: List[str])
    def subscribe_to_events(self, event_types: List[str])
    def publish_event(self, event_type: str, payload: dict)
    def get_project_context(self, project_id: str) -> ProjectContext
    def get_vector_context(self, query: str, project_id: str) -> List[Document]
    def get_graph_relationships(self, entity_id: str) -> GraphResult
    def increment_metric(self, event_type: str, status: str)
```

#### Agent Manager (`agent_manager.py`)
- Manages agent lifecycle and event subscriptions
- Prevents infinite event loops using sliding window detection
- Handles agent throttling and error recovery
- Provides agent health monitoring and metrics
- Respects per-project agent toggles (define_enabled, planner_enabled, build_enabled flags in Project table)

### 2. Specialized Agents

#### Capture Agent (`capture_agent.py`)
**Purpose:** Process incoming Slack messages and external inputs
**Events:** Subscribes to `slack.message.received`, publishes `idea.captured`
**Context:** Uses project system map for entity recognition
**AI Integration:** Claude for content analysis and categorization

#### Define Agent (`define_agent.py`)
**Purpose:** Generate comprehensive specifications from promoted ideas
**Events:** Subscribes to `idea.promoted`, publishes `spec.frozen`
**Context:** pgvector search for similar specs, project documentation
**AI Integration:** Claude with rich context for requirements, design, and task generation
**External Integration:** Optional Notion sync after `spec.frozen` (disabled by default, configured per project)

#### Planner Agent (`planner_agent.py`)
**Purpose:** Break down specifications into actionable tasks with intelligent analysis
**Events:** Subscribes to `spec.frozen`, publishes `tasks.created`
**Context:** Git blame analysis for owner suggestions, team expertise graph, repository structure analysis
**AI Integration:** Claude Code SDK for repository analysis, effort estimation, and dependency detection

#### Build Agent (`build_agent.py`)
**Purpose:** Generate code and create pull requests
**Events:** Subscribes to `task.started`, publishes `build.started`
**Context:** pgvector for similar code, graph for dependencies
**AI Integration:** Claude-Code with comprehensive project context

#### Test Agent (`test_agent.py`)
**Purpose:** Generate tests and analyze quality
**Events:** Subscribes to `build.succeeded`, publishes `quality.analyzed`
**Context:** Code diff analysis, existing test patterns
**AI Integration:** Claude for test generation and failure analysis

#### User Simulation Agent (`user_simulation_agent.py`)
**Purpose:** Run synthetic user testing
**Events:** Subscribes to `deployment.completed`, publishes `user.friction`
**Context:** User personas, historical friction patterns
**AI Integration:** Behavioral analysis and friction detection

#### Learn Agent (`learn_agent.py`)
**Purpose:** Generate insights and continuous improvement recommendations
**Events:** Subscribes to project completion events, publishes `pattern.identified`
**Context:** Historical project data, success/failure patterns
**AI Integration:** Pattern recognition and insight generation

### 3. Context Services (`src/services/`)

#### Vector Context Service (`vector_context_service.py`)
```python
class VectorContextService:
    def find_similar_specs(self, query: str, project_id: str, limit: int = 5)
    def find_similar_code(self, query: str, project_id: str, limit: int = 10)
    def find_related_docs(self, query: str, project_id: str, limit: int = 3)
    def embed_and_store(self, content: str, content_type: str, project_id: str)
```

#### Graph Relationship Service (`graph_service.py`)
```python
class GraphService:
    def get_idea_relationships(self, idea_id: str) -> Dict
    def get_spec_dependencies(self, spec_id: str) -> Dict
    def get_task_connections(self, task_id: str) -> Dict
    def get_team_expertise(self, project_id: str) -> Dict
    def create_relationship(self, from_entity: str, to_entity: str, rel_type: str)
```

#### Claude Code Intelligence Service (`claude_code_intelligence_service.py`)
```python
class ClaudeCodeIntelligenceService:
    def __init__(self, api_key: str, repo_path: str)
    
    async def analyze_repository_structure(self, project_id: str) -> RepositoryAnalysis:
        """Use Claude Code SDK to analyze codebase structure and complexity"""
    
    async def estimate_task_effort(self, task: Task, repo_context: str) -> EffortEstimate:
        """Provide dynamic effort estimation based on code complexity analysis"""
    
    async def suggest_developer_assignment(self, task: Task, team_data: Dict) -> DeveloperSuggestion:
        """Analyze git history and code ownership to suggest optimal developer"""
    
    async def detect_task_dependencies(self, tasks: List[Task], repo_path: str) -> DependencyMap:
        """Use code analysis to detect technical dependencies between tasks"""
    
    async def analyze_code_impact(self, task: Task, repo_path: str) -> CodeImpactAnalysis:
        """Identify which files and components will be affected by task implementation"""
    
    async def assess_implementation_risk(self, task: Task, repo_context: str) -> RiskAssessment:
        """Evaluate complexity factors and potential risks for task implementation"""
    
    async def get_historical_task_patterns(self, task_type: str, repo_path: str) -> List[HistoricalTask]:
        """Analyze git history for similar tasks and their implementation patterns"""
```

### 4. UI Components (`mission-control/src/components/`)

#### Stage Navigation (`StageNav.tsx`)
- Implements seven-stage navigation with progression rules
- Shows health indicators and stage enablement status
- Handles stage transitions and URL routing

#### Think Stage (`ThinkStage.tsx`)
- Feed list with intelligent categorization
- Drag-to-define functionality with visual feedback
- Context panel with relationship display

#### Define Stage (`DefineStage.tsx`)
- Three-tab editor for requirements.md, design.md, tasks.md
- AI-draft vs Human-reviewed badge system
- Freeze specification workflow

#### Plan Stage (`PlanStage.tsx`)
- Intelligent Kanban board with Ready/In Progress/Done lanes
- Dynamic task cards showing AI-generated estimates, developer suggestions, and priority color coding
- Dependency blocking visualization with "Blocked by Task #X" indicators
- Task detail drawer with comprehensive context, code impact analysis, and confidence scores
- Real-time updates via WebSocket with progress message display
- Failed task indicators with red corner badges and retry functionality

#### Build Stage (`BuildStage.tsx`)
- PR monitoring table with CI status
- Build failure analysis and recommendations
- Code preview and branch management

#### Validate Stage (`ValidateStage.tsx`)
- Test execution timeline and results
- Quality analysis and AI-powered insights
- Test coverage and performance metrics

#### User Stage (`UserStage.tsx`)
- User simulation grid with persona and status
- Friction point visualization and replay
- User behavior analysis and recommendations

#### Learn Stage (`LearnStage.tsx`)
- Insight carousel with actionable recommendations
- "Open as idea" functionality for continuous improvement
- Pattern recognition and trend analysis

### 5. Real-Time Communication (`src/services/websocket_server.py`)

#### WebSocket Event Bridge
- Subscribes to Redis events and filters by user permissions
- Broadcasts relevant events to connected clients
- Handles connection management and reconnection logic
- Provides user presence indicators

#### Event Filtering
```python
def filter_events_for_user(user_token: str, event: dict) -> bool:
    user_projects = decode_token(user_token).project_ids
    return event.payload.project_id in user_projects
```

## Claude Code SDK Integration and Sub Agent Architecture

### Sub Agent Orchestration System

#### Sub Agent Detection and Validation
```python
class SubAgentManager:
    def __init__(self, github_service: GitHubService):
        self.github = github_service
        self.required_agents = [
            'feature-builder.md',
            'test-runner.md', 
            'code-reviewer.md',
            'debugger.md',
            'design-to-code.md'
        ]
    
    async def validate_repository_agents(self, repo_url: str, token: str) -> SubAgentStatus:
        """Check for .claude/agents/ directory and validate sub agent files"""
        try:
            agents_dir = await self.github.get_directory_contents(repo_url, '.claude/agents', token)
            available_agents = [f.name for f in agents_dir if f.name.endswith('.md')]
            
            return SubAgentStatus(
                total_required=len(self.required_agents),
                available_count=len([a for a in self.required_agents if a in available_agents]),
                missing_agents=[a for a in self.required_agents if a not in available_agents],
                status='complete' if len(available_agents) == len(self.required_agents) else 'partial'
            )
        except Exception as e:
            return SubAgentStatus(
                total_required=len(self.required_agents),
                available_count=0,
                missing_agents=self.required_agents,
                status='missing',
                error=str(e)
            )
```

#### Intelligent Sub Agent Selection
```python
class SubAgentSelector:
    def __init__(self):
        self.routing_rules = {
            'feature-builder': lambda task: self._is_feature_task(task),
            'test-runner': lambda task: 'test' in task.title.lower() or 'testing' in task.description.lower(),
            'debugger': lambda task: any(keyword in task.title.lower() for keyword in ['bug', 'fix', 'error', 'issue']),
            'code-reviewer': lambda task: any(keyword in task.title.lower() for keyword in ['refactor', 'review', 'optimize']),
            'design-to-code': lambda task: 'figma' in task.description.lower() or 'design' in task.title.lower()
        }
    
    def suggest_agent(self, task: Task) -> AgentSuggestion:
        """Analyze task content and suggest the most appropriate sub agent"""
        for agent_name, rule_func in self.routing_rules.items():
            if rule_func(task):
                return AgentSuggestion(
                    agent_name=agent_name,
                    confidence=0.8,
                    reasoning=f"Task matches {agent_name} pattern based on title/description analysis"
                )
        
        # Default fallback
        return AgentSuggestion(
            agent_name='feature-builder',
            confidence=0.6,
            reasoning="Default selection for general development tasks"
        )
```

#### Claude Code SDK Execution Engine
```python
class ClaudeCodeExecutor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.sdk_options = {
            'max_turns': 10,
            'output_format': 'stream-json',
            'permission_mode': 'acceptEdits'
        }
    
    async def execute_with_sub_agent(self, task: Task, agent_name: str, context: TaskContext, repo_path: str) -> ExecutionResult:
        """Execute task using specified Claude Code sub agent"""
        
        # Prepare the prompt for Claude Code SDK
        prompt = f"Use the {agent_name} sub agent to implement task {task.id}: {task.title}\n\n"
        prompt += f"Task Description: {task.description}\n\n"
        prompt += f"Context: {context.to_prompt_string()}\n\n"
        prompt += "Follow the sub agent's guidelines and tool permissions as defined in the .claude/agents/ configuration."
        
        # Configure SDK options based on sub agent
        options = self._get_agent_specific_options(agent_name)
        
        # Execute using Claude Code SDK
        messages = []
        async for message in query(
            prompt=prompt,
            options=ClaudeCodeOptions(
                cwd=repo_path,
                max_turns=options['max_turns'],
                allowed_tools=options['allowed_tools'],
                **self.sdk_options
            )
        ):
            messages.append(message)
            # Stream progress to UI
            await self._stream_progress_update(task.id, message)
        
        return ExecutionResult(
            task_id=task.id,
            agent_used=agent_name,
            messages=messages,
            success=self._determine_success(messages),
            artifacts=self._extract_artifacts(messages)
        )
    
    def _get_agent_specific_options(self, agent_name: str) -> Dict[str, Any]:
        """Configure tool permissions and options per sub agent"""
        agent_configs = {
            'feature-builder': {
                'max_turns': 15,
                'allowed_tools': ['Read', 'Write', 'Bash']
            },
            'test-runner': {
                'max_turns': 10,
                'allowed_tools': ['Read', 'Write', 'Bash']  # Limited write for test files only
            },
            'code-reviewer': {
                'max_turns': 8,
                'allowed_tools': ['Read', 'Grep', 'Glob']  # Read-only access
            },
            'debugger': {
                'max_turns': 12,
                'allowed_tools': ['Read', 'Write', 'Bash']  # Full access for minimal fixes
            },
            'design-to-code': {
                'max_turns': 20,
                'allowed_tools': ['Read', 'Write', 'Bash']  # Full access, may hand off to other tools
            }
        }
        return agent_configs.get(agent_name, agent_configs['feature-builder'])
```

### Enhanced Plan Stage Design

#### Intelligent Task Card Interface
```typescript
interface IntelligentTaskCard {
  // Core task data
  id: string
  title: string
  task_number: string
  description: string
  
  // AI-generated intelligence
  effort_estimate: {
    hours: number
    confidence: number  // 0-1 scale
    reasoning: string
    historical_comparison: string[]
    cached_until: string  // Cache based on base commit SHA
  }
  
  suggested_developer: {
    name: string
    expertise_match: number  // 0-1 scale
    availability: 'available' | 'busy' | 'unavailable'
    reasoning: string
    git_analysis: {
      files_owned: number
      recent_commits: number
      expertise_areas: string[]
    }
  }
  
  suggested_agent: {
    agent_name: 'feature-builder' | 'test-runner' | 'code-reviewer' | 'debugger' | 'design-to-code'
    confidence: number
    reasoning: string
    can_override: boolean
  }
  
  priority: {
    level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
    color_scheme: string
    auto_adjusted: boolean
    complexity_factors: string[]
  }
  
  dependencies: {
    depends_on: string[]
    blocks: string[]
    is_blocked: boolean
    blocking_tasks: TaskReference[]
    dependency_confidence: number
  }
  
  code_impact: {
    affected_files: string[]
    affected_components: string[]
    risk_level: 'low' | 'medium' | 'high'
    complexity_score: number
    likely_touches: string[]  // Hint for parallel work detection
  }
  
  requirements_refs: string[]
  status: TaskStatus
  github_branch?: string
  pr_url?: string
}
```

#### "Prepare Agent Run" Side Panel
```typescript
interface PrepareAgentRunPanel {
  // GitHub connection status
  github_status: {
    connected: boolean
    repo_name: string
    base_branch: string
    sub_agents_available: number
    connection_message: string  // "Connected • org/repo • base: main • 5 sub agents"
  }
  
  // Agent selection
  agent_selection: {
    suggested_agent: string
    reasoning: string
    available_agents: SubAgentOption[]
    selected_agent: string
    can_override: boolean
  }
  
  // Context configuration
  context_options: {
    spec_files: boolean
    requirements: boolean
    design_notes: boolean
    task_text: boolean
    suggested_code_paths: boolean
    custom_paths: string[]
  }
  
  // Branch configuration
  branch_config: {
    auto_generated_name: string
    base_branch: string
    editable: boolean
    collision_handled: boolean
  }
  
  // Execution plan
  execution_plan: {
    dry_run_description: string  // "Create branch from main → pass spec+design+task → limit writes to ui/theme → run tests → push → open draft PR"
    estimated_duration: string
    will_chain_agents: boolean
    expected_chain: string[]  // e.g., ["feature-builder", "test-runner", "code-reviewer"]
  }
  
  // Actions
  actions: {
    can_start: boolean
    start_button_text: string
    preflight_checks: PreflightCheck[]
  }
}
```

### Agent Chain Execution System

#### Chain Orchestrator
```python
class AgentChainOrchestrator:
    def __init__(self, executor: ClaudeCodeExecutor, github_service: GitHubService):
        self.executor = executor
        self.github = github_service
        self.chain_definitions = {
            'feature-builder': ['test-runner', 'code-reviewer'],
            'test-runner': ['code-reviewer'],
            'debugger': [],  # Usually runs standalone
            'code-reviewer': [],  # Terminal agent
            'design-to-code': ['test-runner', 'code-reviewer']
        }
    
    async def execute_task_with_chaining(self, task: Task, primary_agent: str, context: TaskContext) -> ChainExecutionResult:
        """Execute primary agent and automatically chain follow-up agents"""
        
        chain_results = []
        current_context = context
        
        # Execute primary agent
        primary_result = await self.executor.execute_with_sub_agent(task, primary_agent, current_context, task.repo_path)
        chain_results.append(primary_result)
        
        # Update task status and stream progress
        await self._update_task_progress(task.id, f"{primary_agent} completed", 0.4)
        
        if primary_result.success:
            # Determine next agents in chain
            next_agents = self.chain_definitions.get(primary_agent, [])
            
            for i, next_agent in enumerate(next_agents):
                # Check if we should continue (e.g., tests passed for test-runner)
                if await self._should_continue_chain(chain_results, next_agent):
                    # Update context with previous results
                    updated_context = await self._update_context_with_results(current_context, chain_results)
                    
                    # Execute next agent
                    next_result = await self.executor.execute_with_sub_agent(task, next_agent, updated_context, task.repo_path)
                    chain_results.append(next_result)
                    
                    # Update progress
                    progress = 0.4 + (0.6 * (i + 1) / len(next_agents))
                    await self._update_task_progress(task.id, f"{next_agent} completed", progress)
                    
                    if not next_result.success:
                        # Chain failed, potentially switch to debugger
                        if next_agent != 'debugger':
                            debugger_result = await self.executor.execute_with_sub_agent(task, 'debugger', updated_context, task.repo_path)
                            chain_results.append(debugger_result)
                            await self._update_task_progress(task.id, "debugger completed", 1.0)
                        break
                else:
                    # Chain condition not met, stop here
                    break
        
        return ChainExecutionResult(
            task_id=task.id,
            primary_agent=primary_agent,
            chain_results=chain_results,
            final_status=self._determine_final_status(chain_results),
            pr_url=await self._extract_pr_url(chain_results),
            touched_files=await self._extract_touched_files(chain_results)
        )
```

### GitHub Integration Architecture

#### Branch Management Service
```python
class GitHubBranchManager:
    def __init__(self, github_service: GitHubService):
        self.github = github_service
    
    async def create_task_branch(self, task: Task, base_branch: str = 'main') -> BranchCreationResult:
        """Create a new branch for task execution with collision handling"""
        
        # Generate branch name
        date_suffix = datetime.now().strftime('%Y%m%d')
        task_slug = self._create_slug(task.title)
        task_type = self._determine_task_type(task)
        
        base_name = f"{task_type}/{task.id}-{task_slug}-{date_suffix}"
        
        # Handle collisions
        branch_name = await self._resolve_branch_collision(base_name, task.repo_url, task.github_token)
        
        # Create branch
        try:
            await self.github.create_branch(task.repo_url, branch_name, base_branch, task.github_token)
            
            return BranchCreationResult(
                success=True,
                branch_name=branch_name,
                base_branch=base_branch,
                repo_url=task.repo_url
            )
        except Exception as e:
            return BranchCreationResult(
                success=False,
                error=str(e),
                attempted_name=branch_name
            )
    
    async def _resolve_branch_collision(self, base_name: str, repo_url: str, token: str) -> str:
        """Handle branch name collisions by appending -2, -3, etc."""
        current_name = base_name
        counter = 2
        
        while await self.github.branch_exists(repo_url, current_name, token):
            current_name = f"{base_name}-{counter}"
            counter += 1
        
        return current_name
```

#### Pull Request Automation
```python
class PullRequestManager:
    def __init__(self, github_service: GitHubService):
        self.github = github_service
    
    async def create_task_pr(self, task: Task, branch_name: str, chain_results: List[ExecutionResult]) -> PRCreationResult:
        """Create PR with consistent formatting and task traceability"""
        
        # Generate PR title and body
        pr_title = f"[{task.id}] {task.title}"
        pr_body = self._generate_pr_body(task, chain_results)
        
        # Create draft PR initially
        pr_result = await self.github.create_pull_request(
            repo_url=task.repo_url,
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=task.base_branch,
            draft=True,
            token=task.github_token
        )
        
        if pr_result.success:
            # Run tests and convert to ready if they pass
            test_result = await self._run_tests_and_check(task.repo_path)
            
            if test_result.passed:
                await self.github.mark_pr_ready_for_review(pr_result.pr_url, task.github_token)
                await self._update_task_status(task.id, 'review')
            else:
                await self._update_task_status(task.id, 'failed', test_result.error_summary)
        
        return pr_result
    
    def _generate_pr_body(self, task: Task, chain_results: List[ExecutionResult]) -> str:
        """Generate consistent PR body with task context and agent chain info"""
        body_parts = [
            f"## Task: {task.title}",
            f"**Task ID:** {task.id}",
            f"**Requirements:** {', '.join(task.requirements_refs)}",
            "",
            "## Implementation Summary",
            task.description,
            "",
            "## Agent Chain Execution"
        ]
        
        for result in chain_results:
            body_parts.extend([
                f"### {result.agent_used}",
                f"- **Status:** {'✅ Success' if result.success else '❌ Failed'}",
                f"- **Duration:** {result.duration}",
                f"- **Files Modified:** {len(result.touched_files)} files",
                ""
            ])
        
        if chain_results:
            touched_files = set()
            for result in chain_results:
                touched_files.update(result.touched_files)
            
            body_parts.extend([
                "## Changed Files",
                *[f"- {file}" for file in sorted(touched_files)],
                ""
            ])
        
        return "\n".join(body_parts)
```

### Real-Time Progress Streaming

#### WebSocket Progress Updates
```python
class TaskProgressStreamer:
    def __init__(self, websocket_service: WebSocketService):
        self.websocket = websocket_service
    
    async def stream_task_progress(self, task_id: str, message: str, progress: float, agent_name: str = None, pr_url: str = None):
        """Stream real-time progress updates to UI"""
        
        progress_event = {
            'type': 'task_progress',
            'task_id': task_id,
            'message': message,
            'progress': progress,
            'timestamp': datetime.utcnow().isoformat(),
            'agent_name': agent_name,
            'pr_url': pr_url
        }
        
        # Broadcast to all users with access to this task's project
        await self.websocket.broadcast_to_project(task.project_id, progress_event)
    
    async def stream_agent_chain_update(self, task_id: str, chain_status: List[Dict[str, Any]]):
        """Stream agent chain execution status"""
        
        chain_event = {
            'type': 'agent_chain_update',
            'task_id': task_id,
            'chain_status': chain_status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.websocket.broadcast_to_project(task.project_id, chain_event)
```

## Data Models

### Enhanced Data Models

#### Sub Agent and Execution Models
```python
@dataclass
class SubAgentStatus:
    total_required: int
    available_count: int
    missing_agents: List[str]
    status: str  # 'complete', 'partial', 'missing'
    error: Optional[str] = None

@dataclass
class AgentSuggestion:
    agent_name: str
    confidence: float
    reasoning: str

@dataclass
class ExecutionResult:
    task_id: str
    agent_used: str
    messages: List[Dict[str, Any]]
    success: bool
    artifacts: Dict[str, Any]
    duration: float
    touched_files: List[str]
    pr_url: Optional[str] = None

@dataclass
class ChainExecutionResult:
    task_id: str
    primary_agent: str
    chain_results: List[ExecutionResult]
    final_status: str
    pr_url: Optional[str]
    touched_files: List[str]

@dataclass
class BranchCreationResult:
    success: bool
    branch_name: Optional[str] = None
    base_branch: Optional[str] = None
    repo_url: Optional[str] = None
    error: Optional[str] = None
    attempted_name: Optional[str] = None

@dataclass
class PRCreationResult:
    success: bool
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    error: Optional[str] = None
```

#### Enhanced Task Intelligence Models
```python
@dataclass
class EffortEstimate:
    hours: float
    confidence: float  # 0-1 scale
    reasoning: str
    complexity_factors: List[str]
    historical_comparisons: List[str]
    risk_adjustments: Dict[str, float]
    cached_until: str  # Base commit SHA for cache invalidation

@dataclass
class DeveloperSuggestion:
    developer_name: str
    expertise_match: float  # 0-1 scale
    availability_status: str
    reasoning: str
    git_analysis: Dict[str, Any]
    workload_consideration: float

@dataclass
class DependencyMap:
    task_dependencies: Dict[str, List[str]]
    confidence_scores: Dict[str, float]
    dependency_reasoning: Dict[str, str]
    critical_path: List[str]
    parallel_execution_groups: List[List[str]]

@dataclass
class CodeImpactAnalysis:
    affected_files: List[str]
    affected_components: List[str]
    risk_level: str
    complexity_score: float
    testing_requirements: List[str]
    potential_conflicts: List[str]
    likely_touches: List[str]  # For parallel work detection
```

### Event Schema
```python
@dataclass
class DomainEvent:
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str
    event_type: str
    payload: dict
    source_agent: str
    project_id: str
```

### Project Context
```python
@dataclass
class ProjectContext:
    project_id: str
    system_map: dict
    documentation: List[Document]
    team_members: List[TeamMember]
    git_repository: str
    external_integrations: dict
```

### Database Models

#### Enhanced Task Model
```python
class Task(db.Model):
    id = db.Column(db.String, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey('project.id'))
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum('ready', 'running', 'review', 'done', 'failed'))
    
    # AI-generated intelligence
    suggested_agent = db.Column(db.String)  # Sub agent name
    agent_confidence = db.Column(db.Float)
    agent_reasoning = db.Column(db.Text)
    
    effort_estimate = db.Column(db.Float)  # Hours
    estimate_confidence = db.Column(db.Float)
    estimate_reasoning = db.Column(db.Text)
    estimate_cached_until = db.Column(db.String)  # Base commit SHA
    
    suggested_developer = db.Column(db.String)
    developer_confidence = db.Column(db.Float)
    developer_reasoning = db.Column(db.Text)
    
    priority = db.Column(db.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'))
    
    # GitHub integration
    github_branch = db.Column(db.String)
    pr_url = db.Column(db.String)
    pr_number = db.Column(db.Integer)
    
    # Execution tracking
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    agent_chain = db.Column(db.JSON)  # List of agents used
    touched_files = db.Column(db.JSON)  # List of modified files
    
    # Dependencies
    depends_on = db.Column(db.JSON)  # List of task IDs
    blocks = db.Column(db.JSON)  # List of task IDs
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class TaskExecution(db.Model):
    id = db.Column(db.String, primary_key=True)
    task_id = db.Column(db.String, db.ForeignKey('task.id'))
    agent_name = db.Column(db.String, nullable=False)
    status = db.Column(db.Enum('running', 'completed', 'failed'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    model_turns = db.Column(db.Integer)
    success = db.Column(db.Boolean)
    error_message = db.Column(db.Text)
    correlation_id = db.Column(db.String)  # For debugging
    
    # Results
    touched_files = db.Column(db.JSON)
    pr_url = db.Column(db.String)
    test_results = db.Column(db.JSON)

class Project(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    
    # GitHub integration
    github_repo_url = db.Column(db.String)
    github_token = db.Column(db.String)  # Encrypted
    github_base_branch = db.Column(db.String, default='main')
    github_connected = db.Column(db.Boolean, default=False)
    
    # Sub agent status
    sub_agents_available = db.Column(db.Integer, default=0)
    sub_agents_status = db.Column(db.String, default='missing')  # 'complete', 'partial', 'missing'
    
    # Agent toggles
    define_enabled = db.Column(db.Boolean, default=True)
    planner_enabled = db.Column(db.Boolean, default=True)
    build_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SpecificationArtifact(db.Model):
    id = db.Column(db.String, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey('project.id'))
    artifact_type = db.Column(db.Enum('requirements', 'design', 'tasks'))
    content = db.Column(db.Text)
    status = db.Column(db.Enum('ai_draft', 'human_reviewed', 'frozen'))
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Error Handling

### Agent Error Recovery
- Each agent implements circuit breaker pattern for external API calls
- Failed events are stored in dead letter queue for manual review
- Agent health checks ensure system resilience
- Automatic retry with exponential backoff for transient failures

### Event Processing Guarantees
- At-least-once delivery for critical events
- Idempotency checks prevent duplicate processing
- Event ordering preservation within project scope
- Graceful degradation when external services are unavailable

### User Experience Resilience
- WebSocket reconnection with missed event sync
- Optimistic UI updates with server confirmation
- Fallback to polling when WebSocket unavailable
- Clear error messaging and recovery suggestions

## Testing Strategy

### Agent Testing
- Unit tests for each agent's event processing logic
- Integration tests for agent coordination scenarios
- Mock external services (Slack, GitHub, AI models)
- Event replay testing for complex workflows

### Context Service Testing
- Vector similarity accuracy testing with known datasets
- Graph query performance testing with large datasets
- Context retrieval integration testing
- AI prompt quality validation

### UI Testing
- Component testing for each stage interface
- End-to-end testing for complete user workflows
- WebSocket event handling testing
- Mobile responsiveness and accessibility testing

### Performance Testing
- Event throughput testing under load
- WebSocket connection scaling testing
- Database query optimization validation
- AI response time monitoring

### Monitoring and Observability
- Prometheus metrics collection for all agent operations (success/failure counters by event_type)
- Grafana dashboards for system health, event throughput, and AI response times
- Agent health endpoints for load balancer integration
- Distributed tracing for complex event flows

## Security Considerations

### Authentication and Authorization
- JWT tokens with project-scoped permissions
- Agent-specific service accounts with minimal privileges
- External integration tokens with short expiration
- Audit logging for all security-relevant events

### Data Protection
- Encryption at rest for sensitive project data
- TLS encryption for all external communications
- PII scrubbing in logs and metrics
- GDPR compliance for user data handling

### Agent Security
- Sandboxed execution environment for code generation
- Input validation for all external data sources
- Rate limiting for AI model calls
- Secure credential management for external services

This design provides a comprehensive blueprint for implementing the intelligent Mission Control system while maintaining security, performance, and user experience standards.