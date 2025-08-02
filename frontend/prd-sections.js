// Production-Grade PRD Section Manager - Jony Ive Level Design
class PRDSectionManager {
    constructor() {
        this.sections = new Map();
        this.expandedSections = new Set();
        this.editingSection = null;
        this.sectionTypes = {
            overview: { color: '#4a9eff', icon: '📋', title: 'Overview' },
            features: { color: '#22c55e', icon: '⚡', title: 'Features' },
            requirements: { color: '#f59e0b', icon: '📝', title: 'Requirements' },
            todos: { color: '#fbbf24', icon: '✓', title: 'Action Items' },
            technical: { color: '#8b5cf6', icon: '⚙️', title: 'Technical' },
            timeline: { color: '#ef4444', icon: '📅', title: 'Timeline' },
            risks: { color: '#f97316', icon: '⚠️', title: 'Risks' }
        };
    }

    // Parse PRD content into structured sections
    parsePRDIntoSections(content) {
        // Clean up any JSON wrapper or markdown artifacts
        const cleanContent = this.cleanPRDContent(content);
        const sections = this.extractSections(cleanContent);
        return this.renderSectionInterface(sections);
    }

    // Clean up raw JSON/markdown artifacts
    cleanPRDContent(content) {
        console.log('🧹 Cleaning PRD content:', content.substring(0, 200) + '...');
        
        // Remove JSON wrapper if present
        if (content.includes('"full_prd":') || content.includes('```json')) {
            try {
                // Extract from JSON if wrapped
                const jsonMatch = content.match(/\{[\s\S]*?"full_prd":\s*"([\s\S]*?)"\s*\}/);
                if (jsonMatch) {
                    content = jsonMatch[1];
                    console.log('📦 Extracted from JSON wrapper');
                }
                
                // Remove markdown code blocks
                content = content.replace(/```(?:json|markdown)?\n?/g, '').replace(/```\n?$/g, '');
            } catch (e) {
                console.warn('Failed to parse JSON wrapper, using raw content');
            }
        }

        // Aggressive cleanup of all artifacts
        content = content
            .replace(/^["'`]+|["'`]+$/g, '') // Remove surrounding quotes/backticks
            .replace(/\\n/g, '\n') // Fix escaped newlines
            .replace(/\\"/g, '"') // Fix escaped quotes
            .replace(/\\'/g, "'") // Fix escaped single quotes
            .replace(/\\\\/g, '\\') // Fix double escapes
            .replace(/^\s*\{[\s\S]*?\}\s*$/g, '') // Remove any remaining JSON objects
            .replace(/^\s*\{.*$/gm, '') // Remove lines starting with {
            .replace(/^\s*\}.*$/gm, '') // Remove lines starting with }
            .replace(/^[^#\w\s-].*$/gm, '') // Remove lines that don't start with # or words
            .replace(/\n\s*\n\s*\n/g, '\n\n') // Clean up excessive newlines
            .trim();
        
        console.log('✅ Cleaned content:', content.substring(0, 200) + '...');
        return content;
    }

    // Extract sections from markdown content
    extractSections(content) {
        const sections = [];
        const lines = content.split('\n');
        let currentSection = null;
        let currentContent = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Skip empty lines and artifacts
            if (!line || line.match(/^[{}[\]"'`]+$/)) {
                continue;
            }
            
            // Detect section headers
            if (line.match(/^#{1,3}\s+/)) {
                // Save previous section if it has content
                if (currentSection && currentContent.some(l => l.trim())) {
                    sections.push({
                        ...currentSection,
                        content: currentContent.join('\n').trim()
                    });
                }

                // Start new section
                const level = (line.match(/^#+/) || [''])[0].length;
                const title = line.replace(/^#+\s*/, '').trim();
                
                // Skip if title is empty or looks like an artifact
                if (!title || title.match(/^[{}[\]"'`]+$/)) {
                    continue;
                }
                
                const type = this.detectSectionType(title);
                
                currentSection = {
                    id: this.generateSectionId(title),
                    title,
                    level,
                    type,
                    expanded: level <= 2 // Auto-expand main sections
                };
                currentContent = [];
            } else if (currentSection) {
                currentContent.push(line);
            } else if (line && !currentSection) {
                // Handle content before first header
                if (!sections.length && line.length > 10) {
                    sections.push({
                        id: 'overview',
                        title: 'Overview',
                        level: 1,
                        type: 'overview',
                        expanded: true,
                        content: line
                    });
                }
            }
        }

        // Save last section if it has content
        if (currentSection && currentContent.some(l => l.trim())) {
            sections.push({
                ...currentSection,
                content: currentContent.join('\n').trim()
            });
        }

        // Filter out sections with no meaningful content
        return sections.filter(section => 
            section.content && 
            section.content.length > 5 && 
            !section.content.match(/^[{}[\]"'`\s]*$/)
        );
    }

    // Detect section type based on title
    detectSectionType(title) {
        const titleLower = title.toLowerCase();
        
        if (titleLower.includes('overview') || titleLower.includes('introduction') || titleLower.includes('summary')) {
            return 'overview';
        } else if (titleLower.includes('feature') || titleLower.includes('capability') || titleLower.includes('functionality')) {
            return 'features';
        } else if (titleLower.includes('requirement') || titleLower.includes('specification') || titleLower.includes('criteria')) {
            return 'requirements';
        } else if (titleLower.includes('todo') || titleLower.includes('action') || titleLower.includes('task') || titleLower.includes('checklist')) {
            return 'todos';
        } else if (titleLower.includes('technical') || titleLower.includes('architecture') || titleLower.includes('implementation') || titleLower.includes('api')) {
            return 'technical';
        } else if (titleLower.includes('timeline') || titleLower.includes('roadmap') || titleLower.includes('schedule') || titleLower.includes('milestone')) {
            return 'timeline';
        } else if (titleLower.includes('risk') || titleLower.includes('challenge') || titleLower.includes('issue') || titleLower.includes('concern')) {
            return 'risks';
        }
        
        return 'overview'; // Default
    }

    // Generate unique section ID
    generateSectionId(title) {
        return title.toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
    }

    // Render the beautiful section interface
    renderSectionInterface(sections) {
        const container = document.createElement('div');
        container.className = 'prd-sections-container';
        
        // Add header with controls
        container.appendChild(this.createPRDHeader(sections));
        
        // Add sections
        sections.forEach(section => {
            container.appendChild(this.createSectionElement(section));
        });
        
        // Add "Add Section" button
        container.appendChild(this.createAddSectionButton());
        
        return container;
    }

    // Create PRD header with controls
    createPRDHeader(sections) {
        const header = document.createElement('div');
        header.className = 'prd-header-controls';
        header.innerHTML = `
            <div class="prd-title-section">
                <h1 class="prd-main-title" contenteditable="true">Product Requirements Document</h1>
                <div class="prd-meta-controls">
                    <div class="prd-meta-item">
                        <span class="prd-meta-label">Version:</span>
                        <span class="prd-meta-value" contenteditable="true">1.0</span>
                    </div>
                    <div class="prd-meta-item">
                        <span class="prd-meta-label">Status:</span>
                        <select class="prd-status-select">
                            <option value="draft">Draft</option>
                            <option value="review">In Review</option>
                            <option value="approved">Approved</option>
                        </select>
                    </div>
                    <div class="prd-meta-item">
                        <span class="prd-meta-label">Last Updated:</span>
                        <span class="prd-meta-value">${new Date().toLocaleDateString()}</span>
                    </div>
                </div>
            </div>
            <div class="prd-header-actions">
                <button class="prd-action-btn" onclick="PRDSectionManager.expandAll()">
                    <span class="prd-btn-icon">📖</span>
                    Expand All
                </button>
                <button class="prd-action-btn" onclick="PRDSectionManager.collapseAll()">
                    <span class="prd-btn-icon">📑</span>
                    Collapse All
                </button>
                <button class="prd-action-btn primary" onclick="PRDSectionManager.exportPRD()">
                    <span class="prd-btn-icon">💾</span>
                    Export
                </button>
            </div>
        `;
        
        return header;
    }

    // Create individual section element
    createSectionElement(section) {
        const sectionEl = document.createElement('div');
        const sectionType = this.sectionTypes[section.type] || this.sectionTypes.overview;
        
        sectionEl.className = `prd-section prd-section-${section.type}`;
        sectionEl.setAttribute('data-section-id', section.id);
        
        sectionEl.innerHTML = `
            <div class="prd-section-header" onclick="PRDSectionManager.toggleSection('${section.id}')">
                <div class="prd-section-indicator" style="background: ${sectionType.color}"></div>
                <div class="prd-section-icon">${sectionType.icon}</div>
                <h${section.level + 1} class="prd-section-title" contenteditable="true">${section.title}</h${section.level + 1}>
                <div class="prd-section-controls">
                    <button class="prd-section-btn" onclick="PRDSectionManager.editSection('${section.id}')" title="Edit">
                        <span>✏️</span>
                    </button>
                    <button class="prd-section-btn" onclick="PRDSectionManager.deleteSection('${section.id}')" title="Delete">
                        <span>🗑️</span>
                    </button>
                    <button class="prd-section-toggle ${section.expanded ? 'expanded' : ''}">
                        <span class="prd-toggle-icon">▼</span>
                    </button>
                </div>
            </div>
            <div class="prd-section-content ${section.expanded ? 'expanded' : 'collapsed'}">
                <div class="prd-section-body" contenteditable="true">
                    ${this.renderSectionContent(section.content, section.type)}
                </div>
            </div>
        `;
        
        return sectionEl;
    }

    // Render section content based on type
    renderSectionContent(content, type) {
        if (type === 'todos') {
            return this.renderTodoContent(content);
        } else if (type === 'requirements') {
            return this.renderRequirementsContent(content);
        } else if (type === 'features') {
            return this.renderFeaturesContent(content);
        } else {
            return this.renderGenericContent(content);
        }
    }

    // Render todo items with checkboxes
    renderTodoContent(content) {
        return content
            .split('\n')
            .map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^[-*]\s*\[\s*\]/)) {
                    const text = trimmed.replace(/^[-*]\s*\[\s*\]\s*/, '');
                    return `<div class="prd-todo-item">
                        <input type="checkbox" class="prd-todo-checkbox">
                        <span class="prd-todo-text">${text}</span>
                    </div>`;
                } else if (trimmed.match(/^[-*]\s*\[x\]/i)) {
                    const text = trimmed.replace(/^[-*]\s*\[x\]\s*/i, '');
                    return `<div class="prd-todo-item completed">
                        <input type="checkbox" class="prd-todo-checkbox" checked>
                        <span class="prd-todo-text">${text}</span>
                    </div>`;
                } else if (trimmed) {
                    return `<p>${trimmed}</p>`;
                }
                return '';
            })
            .filter(line => line)
            .join('');
    }

    // Render requirements with priority indicators
    renderRequirementsContent(content) {
        return content
            .split('\n')
            .map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^[-*]\s+/)) {
                    const text = trimmed.replace(/^[-*]\s+/, '');
                    const priority = this.detectPriority(text);
                    return `<div class="prd-requirement-item ${priority}">
                        <span class="prd-priority-indicator"></span>
                        <span class="prd-requirement-text">${text}</span>
                    </div>`;
                } else if (trimmed) {
                    return `<p>${trimmed}</p>`;
                }
                return '';
            })
            .filter(line => line)
            .join('');
    }

    // Render features with status indicators
    renderFeaturesContent(content) {
        return content
            .split('\n')
            .map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^[-*]\s+/)) {
                    const text = trimmed.replace(/^[-*]\s+/, '');
                    return `<div class="prd-feature-item">
                        <span class="prd-feature-icon">⚡</span>
                        <span class="prd-feature-text">${text}</span>
                    </div>`;
                } else if (trimmed) {
                    return `<p>${trimmed}</p>`;
                }
                return '';
            })
            .filter(line => line)
            .join('');
    }

    // Render generic content
    renderGenericContent(content) {
        return content
            .split('\n')
            .map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^[-*]\s+/)) {
                    const text = trimmed.replace(/^[-*]\s+/, '');
                    return `<div class="prd-list-item">
                        <span class="prd-bullet">•</span>
                        <span class="prd-list-text">${text}</span>
                    </div>`;
                } else if (trimmed) {
                    return `<p>${trimmed}</p>`;
                }
                return '';
            })
            .filter(line => line)
            .join('');
    }

    // Detect priority from text
    detectPriority(text) {
        const textLower = text.toLowerCase();
        if (textLower.includes('critical') || textLower.includes('must') || textLower.includes('high')) {
            return 'high';
        } else if (textLower.includes('should') || textLower.includes('medium')) {
            return 'medium';
        } else if (textLower.includes('could') || textLower.includes('low') || textLower.includes('nice')) {
            return 'low';
        }
        return 'medium';
    }

    // Create "Add Section" button
    createAddSectionButton() {
        const button = document.createElement('div');
        button.className = 'prd-add-section';
        button.innerHTML = `
            <button class="prd-add-section-btn" onclick="PRDSectionManager.showAddSectionDialog()">
                <span class="prd-add-icon">+</span>
                Add Section
            </button>
        `;
        return button;
    }

    // Static methods for global access
    static toggleSection(sectionId) {
        const section = document.querySelector(`[data-section-id="${sectionId}"]`);
        const content = section.querySelector('.prd-section-content');
        const toggle = section.querySelector('.prd-section-toggle');
        
        if (content.classList.contains('expanded')) {
            content.classList.remove('expanded');
            content.classList.add('collapsed');
            toggle.classList.remove('expanded');
        } else {
            content.classList.remove('collapsed');
            content.classList.add('expanded');
            toggle.classList.add('expanded');
        }
    }

    static expandAll() {
        document.querySelectorAll('.prd-section-content').forEach(content => {
            content.classList.remove('collapsed');
            content.classList.add('expanded');
        });
        document.querySelectorAll('.prd-section-toggle').forEach(toggle => {
            toggle.classList.add('expanded');
        });
    }

    static collapseAll() {
        document.querySelectorAll('.prd-section-content').forEach(content => {
            content.classList.remove('expanded');
            content.classList.add('collapsed');
        });
        document.querySelectorAll('.prd-section-toggle').forEach(toggle => {
            toggle.classList.remove('expanded');
        });
    }

    static editSection(sectionId) {
        const section = document.querySelector(`[data-section-id="${sectionId}"]`);
        const body = section.querySelector('.prd-section-body');
        body.focus();
        
        // Select all content for easy editing
        const range = document.createRange();
        range.selectNodeContents(body);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    static deleteSection(sectionId) {
        if (confirm('Are you sure you want to delete this section?')) {
            const section = document.querySelector(`[data-section-id="${sectionId}"]`);
            section.remove();
        }
    }

    static showAddSectionDialog() {
        // Create a simple dialog for adding new sections
        const dialog = document.createElement('div');
        dialog.className = 'prd-dialog-overlay';
        dialog.innerHTML = `
            <div class="prd-dialog">
                <h3>Add New Section</h3>
                <input type="text" id="newSectionTitle" placeholder="Section Title" class="prd-dialog-input">
                <select id="newSectionType" class="prd-dialog-select">
                    <option value="overview">📋 Overview</option>
                    <option value="features">⚡ Features</option>
                    <option value="requirements">📝 Requirements</option>
                    <option value="todos">✓ Action Items</option>
                    <option value="technical">⚙️ Technical</option>
                    <option value="timeline">📅 Timeline</option>
                    <option value="risks">⚠️ Risks</option>
                </select>
                <div class="prd-dialog-actions">
                    <button onclick="PRDSectionManager.cancelAddSection()" class="prd-dialog-btn">Cancel</button>
                    <button onclick="PRDSectionManager.confirmAddSection()" class="prd-dialog-btn primary">Add Section</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        document.getElementById('newSectionTitle').focus();
    }

    static cancelAddSection() {
        document.querySelector('.prd-dialog-overlay').remove();
    }

    static confirmAddSection() {
        const title = document.getElementById('newSectionTitle').value;
        const type = document.getElementById('newSectionType').value;
        
        if (title.trim()) {
            const manager = new PRDSectionManager();
            const newSection = manager.createSectionElement({
                id: manager.generateSectionId(title),
                title: title.trim(),
                level: 2,
                type,
                expanded: true,
                content: 'Click to edit this section...'
            });
            
            // Insert before the "Add Section" button
            const addButton = document.querySelector('.prd-add-section');
            addButton.parentNode.insertBefore(newSection, addButton);
        }
        
        PRDSectionManager.cancelAddSection();
    }

    static exportPRD() {
        // Export functionality
        const title = document.querySelector('.prd-main-title').textContent;
        const sections = Array.from(document.querySelectorAll('.prd-section')).map(section => {
            const sectionTitle = section.querySelector('.prd-section-title').textContent;
            const sectionContent = section.querySelector('.prd-section-body').textContent;
            return `## ${sectionTitle}\n\n${sectionContent}\n`;
        });
        
        const markdown = `# ${title}\n\n${sections.join('\n')}`;
        
        // Create download
        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '-').toLowerCase()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Make it globally available
window.PRDSectionManager = PRDSectionManager;

// Test that it's working
console.log('✅ PRDSectionManager loaded successfully');

// Add a simple test method
PRDSectionManager.test = function() {
    console.log('🧪 PRDSectionManager test passed');
    return true;
};