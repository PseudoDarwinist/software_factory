/**
 * Software Factory API Client
 * Unified REST API client replacing Socket.IO with polling
 * Preserves beautiful glass-morphism UI/UX while upgrading architecture
 */

class SoftwareFactoryAPI {
    constructor() {
        this.baseURL = window.location.origin;
        this.polling = {
            statusInterval: null,
            projectsInterval: null,
            isPolling: false,
            statusFrequency: 5000,  // 5 seconds for status
            projectsFrequency: 15000  // 15 seconds for projects
        };
        
        // Event system for UI updates (maintains existing UI patterns)
        this.eventHandlers = new Map();
        
        // Cache for performance
        this.cache = {
            systemStatus: null,
            projects: null,
            aiStatus: null,
            lastUpdate: {
                systemStatus: 0,
                projects: 0,
                aiStatus: 0
            }
        };
        
        // Request queue for managing concurrent requests
        this.requestQueue = new Map();
        
        this.init();
    }
    
    init() {
        console.log('🏭 Software Factory API Client initialized');
        console.log('🎨 Preserving liquid glass aesthetics with enhanced polling');
        
        // Start system monitoring
        this.startPolling();
        
        // Handle page visibility changes for smart polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pausePolling();
            } else {
                this.resumePolling();
            }
        });
        
        // Handle window focus for real-time feel
        window.addEventListener('focus', () => {
            this.immediateRefresh();
        });
    }
    
    // ===== EVENT SYSTEM (maintains existing UI patterns) =====
    
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    // ===== CORE API METHODS =====
    
    async request(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const requestId = `${method}-${endpoint}-${Date.now()}`;
        
        // Prevent duplicate requests
        if (this.requestQueue.has(`${method}-${endpoint}`)) {
            return this.requestQueue.get(`${method}-${endpoint}`);
        }
        
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        if (data && method !== 'GET') {
            config.body = JSON.stringify(data);
        }
        
        const requestPromise = fetch(url, config)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error(`API request failed: ${method} ${endpoint}`, error);
                throw error;
            })
            .finally(() => {
                this.requestQueue.delete(`${method}-${endpoint}`);
            });
        
        this.requestQueue.set(`${method}-${endpoint}`, requestPromise);
        return requestPromise;
    }
    
    // ===== AI SERVICE METHODS (maintains existing AI functionality) =====
    
    async executeGooseTask(instruction, businessContext = {}, githubRepo = null, role = 'business') {
        console.log('🦆 Executing Goose AI task...');
        
        const response = await this.request('POST', '/api/ai/goose/execute', {
            instruction,
            businessContext,
            githubRepo,
            role
        });
        
        // Emit event for UI updates (maintains glass-morphism responsiveness)
        this.emit('ai.response', { provider: 'goose', response });
        
        return response;
    }
    
    async executeModelGardenTask(instruction, productContext = {}, model = 'claude-opus-4', role = 'po') {
        console.log('🏢 Executing Model Garden task...');
        
        const response = await this.request('POST', '/api/ai/model-garden/execute', {
            instruction,
            productContext,
            model,
            role
        });
        
        // Emit event for UI updates
        this.emit('ai.response', { provider: 'model-garden', response });
        
        return response;
    }
    
    async getAIStatus() {
        const response = await this.request('GET', '/api/ai/status');
        this.cache.aiStatus = response;
        this.cache.lastUpdate.aiStatus = Date.now();
        return response;
    }
    
    async getAvailableModels() {
        return this.request('GET', '/api/ai/models');
    }
    
    async testAIIntegrations() {
        return this.request('POST', '/api/ai/test');
    }
    
    // ===== PROJECT MANAGEMENT =====
    
    async getProjects() {
        const response = await this.request('GET', '/api/projects');
        this.cache.projects = response;
        this.cache.lastUpdate.projects = Date.now();
        
        // Emit event for UI updates
        this.emit('projects.updated', response);
        
        return response;
    }
    
    async createProject(projectData) {
        const response = await this.request('POST', '/api/projects', projectData);
        
        // Refresh projects list
        this.getProjects();
        
        // Emit event for UI updates
        this.emit('project.created', response);
        
        return response;
    }
    
    async getProject(projectId) {
        return this.request('GET', `/api/projects/${projectId}`);
    }
    
    async updateProject(projectId, projectData) {
        const response = await this.request('PUT', `/api/projects/${projectId}`, projectData);
        
        // Refresh projects list
        this.getProjects();
        
        // Emit event for UI updates
        this.emit('project.updated', response);
        
        return response;
    }
    
    async deleteProject(projectId) {
        const response = await this.request('DELETE', `/api/projects/${projectId}`);
        
        // Refresh projects list
        this.getProjects();
        
        // Emit event for UI updates
        this.emit('project.deleted', { projectId });
        
        return response;
    }
    
    // ===== SYSTEM STATUS & MONITORING =====
    
    async getSystemStatus() {
        const response = await this.request('GET', '/api/status');
        this.cache.systemStatus = response;
        this.cache.lastUpdate.systemStatus = Date.now();
        
        // Emit event for UI updates (maintains real-time feel for glass UI)
        this.emit('system.status', response);
        
        return response;
    }
    
    async getHealth() {
        return this.request('GET', '/api/health');
    }
    
    async getMetrics() {
        return this.request('GET', '/api/metrics');
    }
    
    // ===== BACKGROUND JOBS =====
    
    async getJobs() {
        return this.request('GET', '/api/jobs');
    }
    
    async getJob(jobId) {
        return this.request('GET', `/api/jobs/${jobId}`);
    }
    
    async cancelJob(jobId) {
        return this.request('POST', `/api/jobs/${jobId}/cancel`);
    }
    
    // ===== POLLING SYSTEM (replaces Socket.IO) =====
    
    startPolling() {
        if (this.polling.isPolling) return;
        
        console.log('🔄 Starting intelligent polling system');
        this.polling.isPolling = true;
        
        // System status polling (frequent for real-time feel)
        this.polling.statusInterval = setInterval(async () => {
            try {
                await this.getSystemStatus();
            } catch (error) {
                console.warn('Status polling failed:', error);
                // Don't break the UI - just log the error
            }
        }, this.polling.statusFrequency);
        
        // Projects polling (less frequent)
        this.polling.projectsInterval = setInterval(async () => {
            try {
                await this.getProjects();
            } catch (error) {
                console.warn('Projects polling failed:', error);
            }
        }, this.polling.projectsFrequency);
        
        // Initial load
        this.immediateRefresh();
    }
    
    pausePolling() {
        console.log('⏸️ Pausing polling (page hidden)');
        if (this.polling.statusInterval) {
            clearInterval(this.polling.statusInterval);
            this.polling.statusInterval = null;
        }
        if (this.polling.projectsInterval) {
            clearInterval(this.polling.projectsInterval);
            this.polling.projectsInterval = null;
        }
        this.polling.isPolling = false;
    }
    
    resumePolling() {
        console.log('▶️ Resuming polling (page visible)');
        this.startPolling();
    }
    
    stopPolling() {
        console.log('🛑 Stopping all polling');
        this.pausePolling();
    }
    
    async immediateRefresh() {
        console.log('⚡ Immediate refresh for real-time UI feel');
        try {
            await Promise.all([
                this.getSystemStatus(),
                this.getProjects(),
                this.getAIStatus()
            ]);
        } catch (error) {
            console.warn('Immediate refresh failed:', error);
        }
    }
    
    // ===== CACHE MANAGEMENT =====
    
    getCachedData(type) {
        const maxAge = 30000; // 30 seconds
        const data = this.cache[type];
        const lastUpdate = this.cache.lastUpdate[type] || 0;
        
        if (data && (Date.now() - lastUpdate) < maxAge) {
            return data;
        }
        
        return null;
    }
    
    clearCache() {
        this.cache = {
            systemStatus: null,
            projects: null,
            aiStatus: null,
            lastUpdate: {
                systemStatus: 0,
                projects: 0,
                aiStatus: 0
            }
        };
        console.log('🧹 Cache cleared');
    }
    
    // ===== UTILITY METHODS =====
    
    setPollingFrequency(statusFreq, projectsFreq) {
        this.polling.statusFrequency = statusFreq;
        this.polling.projectsFrequency = projectsFreq;
        
        if (this.polling.isPolling) {
            this.stopPolling();
            this.startPolling();
        }
    }
    
    getConnectionStatus() {
        return {
            polling: this.polling.isPolling,
            lastStatusUpdate: this.cache.lastUpdate.systemStatus,
            lastProjectsUpdate: this.cache.lastUpdate.projects,
            queuedRequests: this.requestQueue.size
        };
    }
}

// ===== GLOBAL INSTANCE =====

// Create global API instance
window.softwareFactoryAPI = new SoftwareFactoryAPI();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SoftwareFactoryAPI;
}

console.log('🎨 Software Factory API Client loaded - Liquid glass aesthetics preserved!');