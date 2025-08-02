// Beautiful PRD Document Renderer
class PRDRenderer {
    constructor() {
        this.editingElement = null;
        this.tocItems = [];
    }

    // Main method to render PRD content beautifully
    renderPRD(markdownContent, container) {
        if (!container) return;

        // Parse markdown and convert to beautiful HTML
        const htmlContent = this.parseMarkdownToPRD(markdownContent);
        container.innerHTML = htmlContent;

        // Add interactivity
        this.makeEditable(container);
        this.setupTodos(container);
        this.generateTOC(container);
        this.addSmoothScrolling(container);
    }

    // Parse markdown and convert to beautiful PRD HTML
    parseMarkdownToPRD(markdown) {
        let html = '';
        const lines = markdown.split('\n');
        let inCodeBlock = false;
        let inTable = false;
        let tableHeaders = [];
        let currentSection = '';

        // Extract title and metadata
        const titleMatch = markdown.match(/^#\s+(.+)/m);
        const title = titleMatch ? titleMatch[1] : 'Product Requirements Document';

        html += `
            <div class="prd-document">
                <div class="prd-header">
                    <h1 class="prd-title prd-editable" data-type="title">${title}</h1>
                    <p class="prd-subtitle prd-editable" data-type="subtitle">Product Requirements Document</p>
                    <div class="prd-meta">
                        <div class="prd-meta-item">
                            <span class="prd-meta-label">Version:</span>
                            <span class="prd-editable" data-type="version">1.0</span>
                        </div>
                        <div class="prd-meta-item">
                            <span class="prd-meta-label">Last Updated:</span>
                            <span>${new Date().toLocaleDateString()}</span>
                        </div>
                        <div class="prd-meta-item">
                            <span class="prd-meta-label">Status:</span>
                            <span class="prd-priority medium">Draft</span>
                        </div>
                    </div>
                </div>
        `;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();

            // Skip the main title (already handled)
            if (i === 0 && trimmedLine.startsWith('# ')) continue;

            // Handle code blocks
            if (trimmedLine.startsWith('```')) {
                inCodeBlock = !inCodeBlock;
                if (inCodeBlock) {
                    html += '<div class="prd-code">';
                } else {
                    html += '</div>';
                }
                continue;
            }

            if (inCodeBlock) {
                html += this.escapeHtml(line) + '\n';
                continue;
            }

            // Handle headers
            if (trimmedLine.startsWith('## ')) {
                const headerText = trimmedLine.substring(3);
                const headerId = this.generateId(headerText);
                currentSection = headerText;
                html += `<div class="prd-section"><h2 class="prd-h1 prd-editable" id="${headerId}" data-type="h2">${headerText}</h2>`;
                this.tocItems.push({ level: 2, text: headerText, id: headerId });
            } else if (trimmedLine.startsWith('### ')) {
                const headerText = trimmedLine.substring(4);
                const headerId = this.generateId(headerText);
                html += `<h3 class="prd-h2 prd-editable" id="${headerId}" data-type="h3">${headerText}</h3>`;
                this.tocItems.push({ level: 3, text: headerText, id: headerId });
            } else if (trimmedLine.startsWith('#### ')) {
                const headerText = trimmedLine.substring(5);
                const headerId = this.generateId(headerText);
                html += `<h4 class="prd-h3 prd-editable" id="${headerId}" data-type="h4">${headerText}</h4>`;
                this.tocItems.push({ level: 4, text: headerText, id: headerId });
            } else if (trimmedLine.startsWith('##### ')) {
                const headerText = trimmedLine.substring(6);
                html += `<h5 class="prd-h4 prd-editable" data-type="h5">${headerText}</h5>`;
            }
            // Handle lists
            else if (trimmedLine.match(/^[-*+]\s+/)) {
                const listContent = trimmedLine.substring(2);
                
                // Check if it's a todo item
                if (listContent.startsWith('[ ]') || listContent.startsWith('[x]')) {
                    const isChecked = listContent.startsWith('[x]');
                    const todoText = listContent.substring(3).trim();
                    html += this.renderTodo(todoText, isChecked);
                } else {
                    html += `<ul class="prd-list"><li class="prd-list-item prd-editable" data-type="list-item">${this.parseInlineMarkdown(listContent)}</li></ul>`;
                }
            }
            // Handle numbered lists
            else if (trimmedLine.match(/^\d+\.\s+/)) {
                const listContent = trimmedLine.replace(/^\d+\.\s+/, '');
                html += `<ol class="prd-list numbered"><li class="prd-list-item prd-editable" data-type="numbered-item">${this.parseInlineMarkdown(listContent)}</li></ol>`;
            }
            // Handle tables
            else if (trimmedLine.includes('|') && !inTable) {
                inTable = true;
                tableHeaders = trimmedLine.split('|').map(h => h.trim()).filter(h => h);
                html += '<table class="prd-table"><thead><tr>';
                tableHeaders.forEach(header => {
                    html += `<th class="prd-editable" data-type="table-header">${header}</th>`;
                });
                html += '</tr></thead><tbody>';
            } else if (inTable && trimmedLine.includes('|')) {
                if (trimmedLine.match(/^[\s\|:-]+$/)) continue; // Skip separator row
                const cells = trimmedLine.split('|').map(c => c.trim()).filter(c => c);
                html += '<tr>';
                cells.forEach(cell => {
                    html += `<td class="prd-editable" data-type="table-cell">${this.parseInlineMarkdown(cell)}</td>`;
                });
                html += '</tr>';
            } else if (inTable && !trimmedLine.includes('|')) {
                inTable = false;
                html += '</tbody></table>';
                // Process the current line normally
                if (trimmedLine) {
                    html += `<p class="prd-paragraph prd-editable" data-type="paragraph">${this.parseInlineMarkdown(trimmedLine)}</p>`;
                }
            }
            // Handle callouts
            else if (trimmedLine.startsWith('> ')) {
                const calloutContent = trimmedLine.substring(2);
                const calloutType = this.detectCalloutType(calloutContent);
                html += `<div class="prd-callout ${calloutType}">
                    <div class="prd-callout-content prd-editable" data-type="callout">${this.parseInlineMarkdown(calloutContent)}</div>
                </div>`;
            }
            // Handle user stories (special format)
            else if (trimmedLine.startsWith('**User Story:**')) {
                const storyContent = trimmedLine.substring(15).trim();
                html += `<div class="prd-user-story">
                    <div class="prd-user-story-title">User Story</div>
                    <div class="prd-user-story-content prd-editable" data-type="user-story">${this.parseInlineMarkdown(storyContent)}</div>
                </div>`;
            }
            // Handle regular paragraphs
            else if (trimmedLine) {
                // Check if it's a priority or status indicator
                if (trimmedLine.match(/^(High|Medium|Low|Critical|Must Have|Should Have|Could Have|Won't Have):/i)) {
                    const [priority, content] = trimmedLine.split(':', 2);
                    const priorityClass = priority.toLowerCase().replace(/\s+/g, '-');
                    html += `<div class="prd-priority ${this.getPriorityClass(priority)}">${priority}</div>
                             <p class="prd-paragraph prd-editable" data-type="paragraph">${this.parseInlineMarkdown(content.trim())}</p>`;
                } else {
                    const isLead = currentSection === 'Overview' || currentSection === 'Executive Summary';
                    html += `<p class="prd-paragraph ${isLead ? 'lead' : ''} prd-editable" data-type="paragraph">${this.parseInlineMarkdown(trimmedLine)}</p>`;
                }
            }
            // Handle empty lines
            else {
                // Close any open sections
                if (inTable) {
                    inTable = false;
                    html += '</tbody></table>';
                }
            }
        }

        // Close any remaining open sections
        if (inTable) {
            html += '</tbody></table>';
        }

        html += '</div>'; // Close prd-document

        return html;
    }

    // Parse inline markdown (bold, italic, code, links)
    parseInlineMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code class="prd-code-inline">$1</code>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    }

    // Render interactive todo items
    renderTodo(text, isChecked) {
        const todoId = 'todo-' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="prd-todo ${isChecked ? 'completed' : ''}" data-todo-id="${todoId}">
                <div class="prd-todo-checkbox ${isChecked ? 'checked' : ''}" onclick="PRDRenderer.toggleTodo('${todoId}')"></div>
                <div class="prd-todo-text prd-editable" data-type="todo">${this.parseInlineMarkdown(text)}</div>
            </div>
        `;
    }

    // Static method for todo toggling
    static toggleTodo(todoId) {
        const todoElement = document.querySelector(`[data-todo-id="${todoId}"]`);
        const checkbox = todoElement.querySelector('.prd-todo-checkbox');
        
        if (todoElement.classList.contains('completed')) {
            todoElement.classList.remove('completed');
            checkbox.classList.remove('checked');
        } else {
            todoElement.classList.add('completed');
            checkbox.classList.add('checked');
        }
    }

    // Detect callout type based on content
    detectCalloutType(content) {
        const lowerContent = content.toLowerCase();
        if (lowerContent.includes('warning') || lowerContent.includes('caution')) return 'warning';
        if (lowerContent.includes('danger') || lowerContent.includes('error')) return 'danger';
        if (lowerContent.includes('success') || lowerContent.includes('complete')) return 'success';
        return 'info';
    }

    // Get priority class
    getPriorityClass(priority) {
        const p = priority.toLowerCase();
        if (p.includes('high') || p.includes('critical') || p.includes('must')) return 'high';
        if (p.includes('low') || p.includes('could') || p.includes('won\'t')) return 'low';
        return 'medium';
    }

    // Generate ID for headers
    generateId(text) {
        return text.toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
    }

    // Escape HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Make sections editable
    makeEditable(container) {
        const editableElements = container.querySelectorAll('.prd-editable');
        
        editableElements.forEach(element => {
            element.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startEditing(element);
            });
        });

        // Click outside to stop editing
        document.addEventListener('click', (e) => {
            if (this.editingElement && !this.editingElement.contains(e.target)) {
                this.stopEditing();
            }
        });
    }

    // Start editing an element
    startEditing(element) {
        if (this.editingElement) {
            this.stopEditing();
        }

        this.editingElement = element;
        element.classList.add('editing');
        element.contentEditable = true;
        element.focus();

        // Select all text
        const range = document.createRange();
        range.selectNodeContents(element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    // Stop editing
    stopEditing() {
        if (this.editingElement) {
            this.editingElement.classList.remove('editing');
            this.editingElement.contentEditable = false;
            this.editingElement = null;
        }
    }

    // Setup todo functionality
    setupTodos(container) {
        // Already handled in renderTodo method
    }

    // Generate table of contents
    generateTOC(container) {
        if (this.tocItems.length === 0) return;

        const tocHtml = `
            <div class="prd-toc">
                <div class="prd-toc-title">Contents</div>
                <ul class="prd-toc-list">
                    ${this.tocItems.map(item => `
                        <li class="prd-toc-item">
                            <a href="#${item.id}" class="prd-toc-link" data-level="${item.level}">${item.text}</a>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', tocHtml);
    }

    // Add smooth scrolling
    addSmoothScrolling(container) {
        const tocLinks = document.querySelectorAll('.prd-toc-link');
        
        tocLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Get edited content back as markdown
    getMarkdownContent(container) {
        // This would convert the edited HTML back to markdown
        // For now, return a placeholder
        return '# Updated PRD Content\n\nContent has been edited...';
    }
}

// Make it globally available
window.PRDRenderer = PRDRenderer;