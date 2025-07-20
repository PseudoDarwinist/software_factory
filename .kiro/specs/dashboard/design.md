# Design Document

## Overview

The System Monitoring Dashboard is a comprehensive real-time monitoring interface that transforms the Software Factory into an observable system. The design centers around a professional monitoring interface integrated into the Mission Control Settings page, providing complete visibility into events, agents, system health, and integrations.

The system leverages the existing Flask application, PostgreSQL event log, Redis message queue, and WebSocket infrastructure to create a real-time monitoring experience that enables proactive system management and rapid issue resolution.

## Architecture

### High-Level System Flow

```
Event Sources → Event Bus → Monitoring Service → WebSocket → Dashboard UI
     ↓              ↓              ↓              ↓           ↓
Slack/GitHub → Redis Events → Metrics Collection → Real-time → Charts/Grids
Agents       → Database     → Alert Processing   → Updates  → Controls
System       → Logs         → Data Aggregation   → Stream   → Analytics
```

### Real-Time Data Pipeline

The monitoring system uses a multi-layered approach for data collection and presentation:

1. **Event Collection Layer**: Subscribes to all events via Redis and processes them for metrics
2. **Metrics Aggregation Layer**: Collects, processes, and stores metrics data with time-series optimization. Collected counters are exposed at /metrics (port 9100) for Prometheus.
3. **Real-Time Streaming Layer**: Uses WebSocket to push updates to connected dashboard clients. Dashboard clients subscribe to WebSocket topic monitor.events for live events and monitor.metrics for numeric updates.
4. **Presentation Layer**: React-based dashboard with interactive charts and real-time updates

### Data Architecture

```
PostgreSQL (Primary Storage)
├── event_log (existing)           # All system events with full payload
├── monitoring_metrics             # Aggregated metrics and time-series data
├── agent_status                   # Current agent status and performance
├── system_health                  # System component health checks
├── alert_history                  # Alert events and acknowledgments
└── dashboard_config               # User preferences and alert thresholds

**Data Retention**: High-res metrics kept 7 days, then down-sampled to hourly; raw events pruned at 14 days.

Redis (Real-Time Layer)
├── event_stream                   # Live event broadcasting
├── metrics_cache                  # Cached aggregated metrics
├── agent_heartbeats              # Real-time agent status. Agents publish a heartbeat every 5s; status turns yellow at 15s, red at 30s.
└── alert_queue                   # Active alerts and notifications
```

## Components and Interfaces

### Backend Components

#### 1. Monitoring Service (`MonitoringService`)

**Core Responsibilities:**

- Subscribe to all Redis events for real-time processing
- Aggregate metrics and maintain time-series data
- Monitor agent status and performance
- Execute health checks for system components
- Process alerts and notifications

**Key Methods:**

```python
class MonitoringService:
    def collect_event_metrics(self) -> EventMetrics
    def collect_agent_metrics(self) -> Dict[str, AgentMetrics]
    def collect_system_health(self) -> SystemHealth
    def collect_integration_status(self) -> IntegrationStatus
    def process_alerts(self, metrics: AllMetrics) -> List[Alert]
    def stream_to_websocket(self, data: MonitoringData) -> None
```

#### 2. Metrics API (`/api/monitoring/*`)

**Authentication**: All /api/monitoring/* routes reuse the same JWT middleware as the main application.

**Endpoint Structure:**

```python
/api/monitoring/events              # Event stream and analytics
  GET /stream                       # WebSocket endpoint for real-time events
  GET /analytics                    # Historical event analytics
  GET /search                       # Event search and filtering

/api/monitoring/agents              # Agent status and metrics
  GET /status                       # Current status of all agents
  GET /metrics/{agent_id}           # Detailed metrics for specific agent
  POST /control/{agent_id}          # Start/stop/restart agent

/api/monitoring/system              # System health and resources
  GET /health                       # Overall system health score
  GET /resources                    # Resource usage metrics
  GET /components                   # Individual component status

/api/monitoring/integrations        # External service status
  GET /status                       # All integration status
  GET /metrics                      # Integration performance metrics
  POST /test/{integration}          # Test integration connectivity

/api/monitoring/alerts              # Alert configuration and history
  GET /active                       # Current active alerts
  GET /history                      # Alert history and trends
  POST /configure                   # Update alert thresholds
  POST /acknowledge/{alert_id}      # Acknowledge alert
```

#### 3. Alert System (`AlertService`)

**Alert Types:**

- **Critical**: System down, agent failures, integration outages
- **Warning**: Performance degradation, high error rates, resource limits
- **Info**: Configuration changes, maintenance events, usage milestones

**Alert Processing:**

Every alert—no matter who triggers—must be inserted into alert_history before Redis publish to guarantee replay capability.

```python
class AlertService:
    def evaluate_thresholds(self, metrics: Metrics) -> List[Alert]
    def trigger_alert(self, alert: Alert) -> None
    def acknowledge_alert(self, alert_id: str, user: str) -> None
    def escalate_alert(self, alert: Alert) -> None
    def send_notifications(self, alert: Alert) -> None
```

### Frontend Components

#### 1. Settings Page Integration

**Navigation Structure:**

```typescript
/settings
├── /monitoring                    # Main monitoring dashboard
├── /agents                        # Agent configuration (future)
├── /integrations                  # Integration settings (future)
└── /alerts                        # Alert configuration
```

#### 2. Dashboard Layout

**Grid-Based Layout:**

```typescript
<MonitoringDashboard>
  <DashboardHeader /> {/* System health summary */}
  <GridLayout>
    <EventMonitorPanel /> {/* Real-time event stream */}
    <AgentStatusGrid /> {/* Agent status and controls */}
    <SystemHealthPanel /> {/* Infrastructure metrics */}
    <IntegrationStatus /> {/* External service status */}
    <AlertsPanel /> {/* Active alerts and history */}
    <AnalyticsCharts /> {/* Historical trends */}
  </GridLayout>
</MonitoringDashboard>
```

#### 3. Real-Time Event Monitor

**Event Stream Component:**

```typescript
interface EventStreamProps {
  filters: EventFilter[];
  searchQuery: string;
  maxEvents: number;
}

const EventStream: React.FC<EventStreamProps> = ({
  filters,
  searchQuery,
  maxEvents = 100,
}) => {
  // Note: Use the same dark grid texture already in Mission Control for native feel
  const { events, isConnected } = useWebSocketEvents();
  const filteredEvents = useEventFiltering(events, filters, searchQuery);

  return (
    <div className="event-stream">
      <EventFilters />
      <EventList events={filteredEvents} />
      <EventDetails selectedEvent={selectedEvent} />
    </div>
  );
};
```

#### 4. Agent Status Grid

**Agent Monitoring Component:**

```typescript
interface AgentGridProps {
  agents: AgentStatus[];
  onAgentControl: (agentId: string, action: AgentAction) => void;
}

const AgentStatusGrid: React.FC<AgentGridProps> = ({
  agents,
  onAgentControl,
}) => {
  return (
    <div className="agent-grid">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} onControl={onAgentControl} />
      ))}
    </div>
  );
};
```

#### 5. System Health Dashboard

**Health Monitoring Component:**

```typescript
const SystemHealthPanel: React.FC = () => {
  const { health, components } = useSystemHealth();

  return (
    <div className="system-health">
      <HealthScore score={health.overallScore} />
      <ComponentStatus components={components} />
      <ResourceMetrics resources={health.resources} />
      <PerformanceCharts metrics={health.performance} />
    </div>
  );
};
```

## Data Models

### Event Metrics Model

```typescript
interface EventMetrics {
  totalEvents: number;
  eventsPerMinute: number;
  eventsByType: Record<string, number>;
  averageProcessingTime: number;
  errorRate: number;
  recentEvents: Event[];
}
```

### Agent Status Model

```typescript
interface AgentStatus {
  id: string;
  name: string;
  status: "running" | "stopped" | "error" | "paused";
  metrics: {
    eventsProcessed: number;
    successRate: number;
    averageProcessingTime: number;
    currentLoad: number;
    lastActivity: Date;
  };
  configuration: AgentConfig;
  logs: LogEntry[];
}
```

### System Health Model

```typescript
interface SystemHealth {
  overallScore: number; // 0-100
  components: {
    database: ComponentHealth;
    redis: ComponentHealth;
    websocket: ComponentHealth;
    apis: ComponentHealth;
  };
  resources: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    networkLatency: number;
  };
  performance: {
    responseTime: number;
    throughput: number;
    errorRate: number;
  };
}
```

### Alert Model

```typescript
interface Alert {
  id: string;
  type: "critical" | "warning" | "info";
  title: string;
  description: string;
  source: string;
  timestamp: Date;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
  resolved: boolean;
  resolvedAt?: Date;
  metadata: Record<string, any>;
}
```

## User Interface Design

### Visual Design Principles

**Professional Monitoring Aesthetic:**

- **Dark theme** with high contrast for extended viewing
- **Color-coded status indicators**: Green (healthy), Yellow (warning), Red (critical)
- **Grid-based layout** with resizable panels
- **Consistent typography** using system fonts
- **Minimal animations** focused on data updates

### Cyber-Grid Visual Theme

The dashboard implements a sophisticated "cyber-grid" aesthetic with dark backgrounds, fine grid lines, and shadowy gradient charts that create a professional monitoring interface.

#### Global Theme Tokens

```css
:root {
  /* surfaces */
  --bg-base: #0d0f14;          /* almost-black charcoal */
  --bg-panel: #151821;         /* slightly lighter card */
  
  /* text */
  --txt-main:  #f5f7fa;
  --txt-dim:   #6b7280;
  
  /* brand accents (chart fills & alert badges) */
  --accent-red:   #ef4444;
  --accent-amber: #f59e0b;
  --accent-green: #10b981;
  --accent-blue:  #3b82f6;
  --accent-purple:#8b5cf6;
  
  /* borders */
  --border-soft: rgba(255,255,255,.05);
}
```

#### Grid Paper Backdrop

```css
.bg-grid {
  background:
    /* vertical lines */
    repeating-linear-gradient(
      to right,
      transparent 0 59px,
      rgba(255,255,255,.03) 59px 60px
    ),
    /* horizontal lines */
    repeating-linear-gradient(
      to bottom,
      transparent 0 59px,
      rgba(255,255,255,.03) 59px 60px
    ),
    var(--bg-panel);
}
```

Apply `.bg-grid` to each metric card and to the whole dashboard body.

#### Metric Stat Block Card

```jsx
<div className="bg-grid rounded-xl p-5 border border-[var(--border-soft)]">
  <header className="flex justify-between items-center mb-4">
    <span className="text-sm uppercase tracking-wide text-[var(--txt-dim)]">
      API Response time
    </span>
    <AlertTriangleIcon className="text-[var(--accent-red)]" />
  </header>
  
  <h2 className="text-3xl font-semibold">9.2 s</h2>
  
  <p className="mt-2 text-xs text-[var(--accent-red)]">
    ↑ 18 300 % from baseline
  </p>
</div>
```

#### Area Chart Component (Recharts)

```jsx
<ResponsiveContainer height={160}>
  <AreaChart data={data}>
    <defs>
      <linearGradient id="grad-red" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%"   stopColor="var(--accent-red)" stopOpacity="0.6" />
        <stop offset="100%" stopColor="var(--accent-red)" stopOpacity="0.05"/>
      </linearGradient>
    </defs>
    
    <Area
      type="monotone"
      dataKey="value"
      stroke="var(--accent-red)"
      strokeWidth={2}
      fill="url(#grad-red)"
      dot={false}
    />
  </AreaChart>
</ResponsiveContainer>
```

Repeat with `grad-amber`, `grad-green`, `grad-blue` for the other mini-charts.

#### Layout Grid

Tailwind / CSS grid: `grid-cols-12 gap-6`

- **Top row**: four stat blocks (`col-span-3` each)
- **Middle row**: three sparkline area-charts (`col-span-4`)
- **Bottom row**: world-map impact (`col-span-6`) + network throughput chart (`col-span-6`)

#### Shadowy Glow on Charts

```css
svg .recharts-area {
  filter: drop-shadow(0 0 4px currentColor);
}
```

#### Motion Rules (Subtle)

- Fade-in new data points with a 150ms CSS opacity transition
- No zoom/pan animation; keep it calm for ops folks

#### Color/Alert Mapping

| Severity | Accent Token | Used For |
|----------|-------------|----------|
| Critical | `--accent-red` | failed requests, build errors |
| Warning | `--accent-amber` | rising latency, CPU > 80% |
| Healthy | `--accent-green` | pass rates, agent up |
| Info | `--accent-blue` | deploy complete, FYI events |

If you have purple charts, use them for "other" metrics to avoid confusion.

#### UX Copy Hints

- Tooltip on stat block header: "Last 5 min"
- Hover on chart shows exact timestamp + value
- Clicking a stat block jumps into the detailed log filtered for that metric

### Responsive Breakpoints

```css
/* Desktop First Approach */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}

/* Tablet */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(8, 1fr);
  }
}

/* Mobile */
@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
```

## Error Handling

### Backend Error Handling

**Monitoring Service Resilience:**

- Graceful degradation when external services are unavailable
- Circuit breaker pattern for external API calls
- Automatic retry with exponential backoff
- Fallback to cached data when real-time data is unavailable

**API Error Responses:**

```typescript
interface ErrorResponse {
  error: string;
  message: string;
  code: number;
  timestamp: Date;
  requestId: string;
}
```

### Frontend Error Handling

**Error Boundary Implementation:**

```typescript
class MonitoringErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to monitoring system
    this.logError(error, errorInfo);

    // Show fallback UI
    this.setState({ hasError: true });
  }

  render() {
    if (this.state.hasError) {
      return <MonitoringErrorFallback />;
    }

    return this.props.children;
  }
}
```

## Testing Strategy

### Backend Testing

**Unit Tests:**

- Monitoring service metric collection
- Alert threshold evaluation
- API endpoint responses
- WebSocket message handling

**Integration Tests:**

- End-to-end event flow monitoring
- Database query performance
- Redis pub/sub functionality
- External service integration

### Frontend Testing

**Component Tests:**

- Event stream rendering and filtering
- Agent status grid interactions
- Chart data visualization
- Real-time update handling

**E2E Tests:**

- Complete dashboard loading and navigation
- Real-time data updates
- Alert acknowledgment workflow
- Mobile responsive behavior

### Performance Testing

**Load Testing:**

- Dashboard performance with 1000+ events/minute (load script will simulate 2k events/min for headroom)
- Concurrent user access (10+ simultaneous users)
- WebSocket connection stability
- Memory usage under sustained load

**Monitoring Impact Testing:**

- System resource usage with monitoring active
- Performance impact on monitored services
- Data retention and cleanup efficiency
