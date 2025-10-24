// Software Factory - Intelligent PRD Editor
// Enhanced with Comprehensive AI Chat and Document Generation
// Professional PRD creation with drilling conversation flow

(function () {
  'use strict';

  let editor;
  let outline = [];
  let currentPRDId = null;
  let currentProjectId = null;
  let websocketConnection = null;
  let collaborationState = {
    users: new Map(),
    cursors: new Map(),
    lastSyncTime: 0,
    isConnected: false
  };

  // Enhanced AI Chat Message Handler with Two-Path Support
  let conversationState = {
    mode: null, // 'modify' or 'create'
    stage: 'initial', // initial, gathering, confirming, generating, modifying
    context: {},
    history: [],
    questionHistory: [],
    currentTopic: null,
    documentsToGenerate: []
  };

  // Ensure Editor.js core and required tools are available (no fallbacks)
  function waitForEditorJSTools(timeoutMs = 8000) {
    const start = Date.now();
    const needed = [
      () => window.EditorJS,
      () => window.Header,
      () => window.Paragraph,
      () => window.List,
      () => window.Quote,
      () => window.Table,
      () => window.RawTool,
      () => window.Delimiter
    ];

    return new Promise((resolve, reject) => {
      const check = () => {
        if (needed.every(fn => {
          try { return !!fn(); } catch { return false; }
        })) {
          return resolve();
        }
        if (Date.now() - start > timeoutMs) {
          return reject(new Error('Editor.js tools not loaded in time'));
        }
        setTimeout(check, 100);
      };
      check();
    });
  }

  // Initialize the editor
  function initializeEditor() {
    const tools = {};
    tools.header = {
      class: window.Header,
      inlineToolbar: ['link'],
      config: { levels: [1, 2, 3, 4, 5, 6], defaultLevel: 2 }
    };
    tools.paragraph = { class: window.Paragraph, inlineToolbar: true };
    tools.list = { class: window.List, inlineToolbar: true };
    tools.quote = window.Quote;
    tools.table = window.Table;
    tools.raw = window.RawTool;
    tools.delimiter = window.Delimiter;

    // Add custom tools into the tools map
    tools.section = {
      class: class {
        constructor({ data }) {
          this.data = data;
          this.wrapper = undefined;
        }
        render() {
          this.wrapper = document.createElement('div');
          this.wrapper.classList.add('section-block');
          const title = document.createElement('h3');
          title.classList.add('section-title');
          title.contentEditable = true;
          title.innerHTML = this.data.title || 'Section Title';
          const content = document.createElement('div');
          content.classList.add('section-content');
          content.contentEditable = true;
          content.innerHTML = this.data.html || '<p>Section content...</p>';
          this.wrapper.appendChild(title);
          this.wrapper.appendChild(content);
          return this.wrapper;
        }
        save() {
          const title = this.wrapper.querySelector('.section-title');
          const content = this.wrapper.querySelector('.section-content');
          return { title: title.innerHTML, html: content.innerHTML };
        }
      }
    };

    tools.mermaid = {
      class: class {
        constructor({ data }) {
          this.data = data || {};
          this.wrapper = undefined;
        }
        render() {
          this.wrapper = document.createElement('div');
          this.wrapper.classList.add('mermaid-block');
          const toolbar = document.createElement('div');
          toolbar.classList.add('mermaid-toolbar');
          toolbar.innerHTML = `
            <button class="btn-edit-mermaid">Edit</button>
            <button class="btn-export-svg">Export SVG</button>
            <button class="btn-export-png">Export PNG</button>
          `;
          const container = document.createElement('div');
          container.classList.add('mermaid-container');
          container.innerHTML = `<div class="mermaid">${this.data.code || 'graph TD\n  A --> B'}</div>`;
          this.wrapper.appendChild(toolbar);
          this.wrapper.appendChild(container);
          toolbar.querySelector('.btn-edit-mermaid').addEventListener('click', () => {
            this.editMermaid();
          });
          return this.wrapper;
        }
        editMermaid() {
          const modal = document.createElement('div');
          modal.classList.add('modal');
          modal.innerHTML = `
            <div class="modal-content">
              <h3>Edit Mermaid Diagram</h3>
              <textarea class="mermaid-editor">${this.data.code || ''}</textarea>
              <div class="modal-buttons">
                <button class="btn-save">Save</button>
                <button class="btn-cancel">Cancel</button>
              </div>
            </div>
          `;
          document.body.appendChild(modal);
          modal.querySelector('.btn-save').addEventListener('click', () => {
            const newCode = modal.querySelector('.mermaid-editor').value;
            this.data.code = newCode;
            this.wrapper.querySelector('.mermaid').innerHTML = newCode;
            renderAllMermaidDiagrams();
            document.body.removeChild(modal);
          });
          modal.querySelector('.btn-cancel').addEventListener('click', () => {
            document.body.removeChild(modal);
          });
        }
        save() { return { code: this.data.code || '' }; }
      }
    };

    const editorConfig = {
      holder: 'editorjs',
      placeholder: 'Start writing your PRD content...',
      tools: tools,
      onChange: () => {
        buildOutline();
      }
    };

    editor = new EditorJS(editorConfig);
  }

  // Load PRD content
  async function loadPRDContent() {
    const urlParams = new URLSearchParams(window.location.search);
    const mock = urlParams.get('mock');
    const projectId = urlParams.get('projectId');
    const prdId = urlParams.get('prdId');
    const version = urlParams.get('version');
    const token = urlParams.get('token');

    const authHeaders = {};
    if (token) {
      authHeaders['Authorization'] = `Bearer ${token}`;
    }

    // Remember IDs for collaboration and saves
    if (projectId) currentProjectId = projectId;
    if (prdId) currentPRDId = prdId;

    // If no prdId, create a new empty document
    if (!prdId) {
      // Create empty Editor.js structure
      const emptyContent = {
        "time": Date.now(),
        "blocks": [
          {
            "id": "empty-header",
            "type": "header",
            "data": { "text": "Product Requirements Document", "level": 1 }
          },
          {
            "id": "empty-paragraph",
            "type": "paragraph",
            "data": { "text": "Start writing your PRD here or use the AI chat to generate content..." }
          }
        ],
        "version": "2.28.2"
      };

      try {
        await editor.render(emptyContent);
        document.body.classList.add('editorjs-ready');
        buildOutline();

        // Initialize Notion-like block editor
        setTimeout(() => {
          if (window.NotionBlockEditor && editor) {
            console.log('🎨 Initializing Notion-like block editor...');
            const editorContainer = document.getElementById('editorjs');
            if (editorContainer) {
              window.notionEditor = new NotionBlockEditor(editorContainer, editor);
              console.log('✅ Notion-like editor initialized');
            }
          }
        }, 1000);

        return;
      } catch (e) {
        console.error('Failed to initialize empty editor:', e);
        const container = document.getElementById('editorjs');
        if (container) {
          container.innerHTML = '<div style="padding:16px;border:1px solid #e2e8f0;border-radius:8px;background:#fff7ed;color:#9a3412;">Failed to initialize editor. Please refresh the page.</div>';
        }
        return;
      }
    }

    // Load actual PRD when ID is provided
    if (prdId) {
      try {
        const qs = version ? `?version=${encodeURIComponent(version)}` : '';
        const response = await fetch(`/api/prd-editor/prds/${encodeURIComponent(prdId)}${qs}`, {
          headers: authHeaders
        });
        if (!response.ok) {
          const container = document.getElementById('editorjs');
          if (container) {
            container.innerHTML = `<div style=\"padding:16px;border:1px solid #e2e8f0;border-radius:8px;background:#fff7ed;color:#9a3412;\">Failed to load PRD (${response.status}).</div>`;
          }
          return;
        }
        const raw = await response.json();
        const payload = raw?.data || raw;
        const maybe = payload?.editorjs_content || payload?.content || payload;
        const hasBlocks = maybe && Array.isArray(maybe.blocks) && maybe.blocks.length > 0;
        if (!hasBlocks) {
          const container = document.getElementById('editorjs');
          if (container) {
            container.innerHTML = '<div style="padding:16px;border:1px solid #e2e8f0;border-radius:8px;background:#fff7ed;color:#9a3412;">No content blocks found for this PRD.</div>';
          }
          return;
        }
        await editor.render(maybe);
        document.body.classList.add('editorjs-ready');
        buildOutline();
        setTimeout(renderAllMermaidDiagrams, 500);

        // Initialize Notion-like block editor after content is rendered
        setTimeout(() => {
          if (window.NotionBlockEditor && editor) {
            console.log('🎨 Initializing Notion-like block editor...');
            const editorContainer = document.getElementById('editorjs');
            if (editorContainer) {
              window.notionEditor = new NotionBlockEditor(editorContainer, editor);
              console.log('✅ Notion-like editor initialized');
            }
          }
        }, 1000); // Wait 1 second for content to render

        return; // done
      } catch (e) {
        console.warn('Failed to load PRD by ID', e);
        const container = document.getElementById('editorjs');
        if (container) {
          container.innerHTML = '<div style="padding:16px;border:1px solid #e2e8f0;border-radius:8px;background:#fff7ed;color:#9a3412;">Error loading PRD. See console for details.</div>';
        }
        return;
      }
    }
  }

  // Build outline navigation
  function buildOutline() {
    editor.save().then(outputData => {
      outline = [];
      const outlineContainer = document.getElementById('outline-list');
      if (!outlineContainer) return;
      outlineContainer.innerHTML = '';

      outputData.blocks.forEach((block, index) => {
        if (block.type === 'header' || block.type === 'section') {
          const level = block.type === 'section' ? 2 : (block.data.level || 2);
          const text = block.type === 'section' ? block.data.title : block.data.text;

          outline.push({ level, text, index });

          const outlineItem = document.createElement('div');
          outlineItem.classList.add('outline-item', `level-${level}`);
          outlineItem.innerHTML = `<span>${text}</span>`;

          outlineItem.addEventListener('click', () => {
            scrollToBlock(index);
          });

          outlineContainer.appendChild(outlineItem);
        }
      });
    });
  }

  // Scroll to specific block
  function scrollToBlock(index) {
    const blocks = document.querySelectorAll('.ce-block');
    if (blocks[index]) {
      blocks[index].scrollIntoView({ behavior: 'smooth' });
    }
  }

  // Render Mermaid diagrams
  function renderAllMermaidDiagrams() {
    if (!window.mermaid || typeof mermaid.render !== 'function') return;
    const mermaidElements = document.querySelectorAll('.mermaid');
    mermaidElements.forEach(element => {
      if (!element.hasAttribute('data-processed')) {
        try {
          mermaid.render('mermaid-' + Math.random().toString(36).substr(2, 9), element.textContent, (svgCode) => {
            element.innerHTML = svgCode;
            element.setAttribute('data-processed', 'true');
          });
        } catch (error) {
          console.error('Mermaid rendering error:', error);
          element.innerHTML = `<div class="mermaid-error">Error rendering diagram: ${error.message}</div>`;
        }
      }
    });
  }

  // Export Functions
  async function exportDocument(format, options = {}) {
    try {
      // Show loading state
      showExportLoading(format);

      // Get current document content
      const content = await editor.save();

      // Prepare export request
      const exportData = {
        content: content,
        format: format,
        options: {
          title: document.title || 'Product Requirements Document',
          include_metadata: true,
          ...options
        }
      };

      // Call export API
      const response = await fetch('/api/prd-editor/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(exportData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Export failed');
      }

      // Handle file download
      const blob = await response.blob();
      const filename = getFilenameFromResponse(response, format);
      downloadBlob(blob, filename);

      hideExportLoading();
      showExportSuccess(format);

    } catch (error) {
      console.error('Export error:', error);
      hideExportLoading();
      showExportError(error.message);
    }
  }

  function getFilenameFromResponse(response, format) {
    const contentDisposition = response.headers.get('Content-Disposition');
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
      if (filenameMatch) {
        return filenameMatch[1];
      }
    }

    // Fallback filename
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const extensions = { pdf: 'pdf', docx: 'docx', markdown: 'md', html: 'html' };
    return `prd_${timestamp}.${extensions[format] || 'txt'}`;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function showExportLoading(format) {
    const button = document.querySelector(`[data-export-format="${format}"]`);
    if (button) {
      button.disabled = true;
      button.innerHTML = `<span class="loading-spinner"></span> Exporting...`;
    }
  }

  function hideExportLoading() {
    document.querySelectorAll('[data-export-format]').forEach(button => {
      button.disabled = false;
      const format = button.dataset.exportFormat;
      const labels = {
        pdf: '📄 Export PDF',
        docx: '📝 Export Word',
        markdown: '📋 Export Markdown',
        html: '🌐 Export HTML'
      };
      button.innerHTML = labels[format] || 'Export';
    });
  }

  function showExportSuccess(format) {
    const notification = document.createElement('div');
    notification.className = 'export-notification success';
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">✅</span>
        <span class="notification-message">${format.toUpperCase()} export completed successfully!</span>
      </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => document.body.removeChild(notification), 300);
    }, 3000);
  }

  function showExportError(message) {
    const notification = document.createElement('div');
    notification.className = 'export-notification error';
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">❌</span>
        <span class="notification-message">Export failed: ${message}</span>
      </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => document.body.removeChild(notification), 300);
    }, 5000);
  }

  async function showExportDialog() {
    try {
      // Get available formats and options
      const [formatsResponse, optionsResponse] = await Promise.all([
        fetch('/api/prd-editor/export/formats'),
        fetch('/api/prd-editor/export/options')
      ]);

      const formatsData = await formatsResponse.json();
      const optionsData = await optionsResponse.json();

      if (!formatsData.success || !optionsData.success) {
        throw new Error('Failed to load export options');
      }

      // Create export dialog
      const dialog = createExportDialog(formatsData.formats, optionsData.options);
      document.body.appendChild(dialog);

      // Show dialog
      setTimeout(() => dialog.classList.add('show'), 10);

    } catch (error) {
      console.error('Error showing export dialog:', error);
      showExportError('Failed to load export options');
    }
  }

  function createExportDialog(formats, options) {
    const dialog = document.createElement('div');
    dialog.className = 'export-dialog-overlay';

    const formatCards = Object.entries(formats).map(([key, format]) => `
      <div class="export-format-card ${!format.available ? 'disabled' : ''}" data-format="${key}">
        <div class="format-header">
          <h3>${format.name}</h3>
          <span class="format-extension">.${format.extension}</span>
        </div>
        <p class="format-description">${format.description}</p>
        <div class="format-features">
          ${format.features.map(feature => `<span class="feature-tag">${feature}</span>`).join('')}
        </div>
        ${!format.available ? '<div class="unavailable-notice">Not available</div>' : ''}
      </div>
    `).join('');

    dialog.innerHTML = `
      <div class="export-dialog">
        <div class="export-dialog-header">
          <h2>Export Document</h2>
          <button class="close-dialog" onclick="closeExportDialog()">&times;</button>
        </div>
        
        <div class="export-dialog-body">
          <div class="export-step">
            <h3>1. Choose Format</h3>
            <div class="export-formats">
              ${formatCards}
            </div>
          </div>
          
          <div class="export-step">
            <h3>2. Export Options</h3>
            <div class="export-options" id="exportOptions">
              <p class="select-format-message">Select a format to see available options</p>
            </div>
          </div>
        </div>
        
        <div class="export-dialog-footer">
          <button class="btn-cancel" onclick="closeExportDialog()">Cancel</button>
          <button class="btn-export" id="exportButton" disabled onclick="performExport()">Export</button>
        </div>
      </div>
    `;

    // Add event listeners for format selection
    dialog.querySelectorAll('.export-format-card:not(.disabled)').forEach(card => {
      card.addEventListener('click', () => {
        // Remove previous selection
        dialog.querySelectorAll('.export-format-card').forEach(c => c.classList.remove('selected'));

        // Select current format
        card.classList.add('selected');

        // Update options panel
        const format = card.dataset.format;
        updateExportOptions(format, options[format] || {});

        // Enable export button
        document.getElementById('exportButton').disabled = false;
      });
    });

    return dialog;
  }

  function updateExportOptions(format, formatOptions) {
    const optionsContainer = document.getElementById('exportOptions');

    if (Object.keys(formatOptions).length === 0) {
      optionsContainer.innerHTML = '<p class="no-options">No additional options available for this format</p>';
      return;
    }

    const optionsHtml = Object.entries(formatOptions).map(([key, option]) => {
      if (option.type === 'boolean') {
        return `
          <div class="export-option">
            <label class="checkbox-label">
              <input type="checkbox" name="${key}" ${option.default ? 'checked' : ''}>
              <span class="checkbox-text">${option.description}</span>
            </label>
          </div>
        `;
      } else if (option.type === 'select') {
        const optionsHtml = option.options.map(opt =>
          `<option value="${opt}" ${opt === option.default ? 'selected' : ''}>${opt}</option>`
        ).join('');

        return `
          <div class="export-option">
            <label class="select-label">
              <span class="select-text">${option.description}</span>
              <select name="${key}">
                ${optionsHtml}
              </select>
            </label>
          </div>
        `;
      }

      return '';
    }).join('');

    optionsContainer.innerHTML = optionsHtml;
  }

  function closeExportDialog() {
    const dialog = document.querySelector('.export-dialog-overlay');
    if (dialog) {
      dialog.classList.add('fade-out');
      setTimeout(() => document.body.removeChild(dialog), 300);
    }
  }

  async function performExport() {
    const dialog = document.querySelector('.export-dialog-overlay');
    const selectedFormat = dialog.querySelector('.export-format-card.selected');

    if (!selectedFormat) {
      showExportError('Please select an export format');
      return;
    }

    const format = selectedFormat.dataset.format;

    // Collect export options
    const options = {};
    const optionInputs = dialog.querySelectorAll('#exportOptions input, #exportOptions select');

    optionInputs.forEach(input => {
      if (input.type === 'checkbox') {
        options[input.name] = input.checked;
      } else {
        options[input.name] = input.value;
      }
    });

    // Close dialog
    closeExportDialog();

    // Perform export
    await exportDocument(format, options);
  }

  // AI Chat Functions
  // Split chat variables
  let chatWidth = parseInt(localStorage.getItem('aiChatWidth') || '400', 10);
  let isChatOpen = (localStorage.getItem('aiChatOpen') === 'true');
  let isChatResizing = false;

  function ensureResizeHandle() {
    if (document.getElementById('chatResizeHandle')) return;
    const handle = document.createElement('div');
    handle.id = 'chatResizeHandle';
    handle.className = 'chat-resize-handle';
    document.body.appendChild(handle);

    // Resize handlers
    handle.addEventListener('mousedown', (e) => {
      isChatResizing = true;
      document.body.style.userSelect = 'none';
    });
    handle.addEventListener('dblclick', () => {
      chatWidth = 420;
      updateChatLayout(true);
    });
    window.addEventListener('mousemove', (e) => {
      if (!isChatResizing) return;
      const viewportWidth = window.innerWidth;
      chatWidth = Math.min(Math.max(300, viewportWidth - e.clientX), 700);
      updateChatLayout();
    });
    window.addEventListener('mouseup', () => {
      if (isChatResizing) {
        isChatResizing = false;
        document.body.style.userSelect = '';
        try { localStorage.setItem('aiChatWidth', String(chatWidth)); } catch (e) { }
      }
    });
  }

  function updateChatLayout(persist = false) {
    const chatPanel = document.getElementById('aiChatPanel');
    const handle = document.getElementById('chatResizeHandle');
    document.documentElement.style.setProperty('--chat-width', chatWidth + 'px');
    if (chatPanel) chatPanel.style.width = chatWidth + 'px';
    if (handle) handle.style.right = chatWidth + 'px';
    if (persist) {
      try { localStorage.setItem('aiChatWidth', String(chatWidth)); } catch (e) { }
    }
  }

  function toggleAiChat() {
    const chatPanel = document.getElementById('aiChatPanel');
    const chatBubble = document.querySelector('.ai-bubble');

    if (!chatPanel) return;

    if (isChatOpen) {
      // Close chat
      document.body.classList.remove('split-chat-open');
      if (chatBubble) chatBubble.style.display = 'flex';
      if (chatPanel) chatPanel.classList.remove('open');
      const handle = document.getElementById('chatResizeHandle');
      if (handle) handle.style.display = 'none';
      isChatOpen = false;
      try { localStorage.setItem('aiChatOpen', 'false'); } catch (e) { }
    } else {
      // Open chat
      ensureResizeHandle();
      updateChatLayout();
      document.body.classList.add('split-chat-open');
      if (chatBubble) chatBubble.style.display = 'none';
      chatPanel.classList.add('open');
      const handle = document.getElementById('chatResizeHandle');
      if (handle) handle.style.display = 'block';
      isChatOpen = true;
      try { localStorage.setItem('aiChatOpen', 'true'); } catch (e) { }

      // Show initial path selection if chat is empty
      showInitialPathSelection();
    }
  }

  function showInitialPathSelection() {
    const chatBody = document.getElementById('chatBody');
    if (!chatBody) return;

    // Clear any existing messages and show path selection
    chatBody.innerHTML = '';

    // Always show path selection when chat opens
    // Show initial path selection
    const pathSelectionDiv = document.createElement('div');
    pathSelectionDiv.className = 'chat-message ai initial-path-selection';
    pathSelectionDiv.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 8px;">AI Assistant</div>
        <div>How would you like to proceed?</div>
        <div class="compact-path-selection">
          <button class="compact-path-card" onclick="selectPath('modify')" data-path="modify">
            Modify Current PRD
          </button>
          <button class="compact-path-card" onclick="selectPath('create')" data-path="create">
            Generate New PRD from Idea
          </button>
        </div>
      `;
    chatBody.appendChild(pathSelectionDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function showTyping() {
    const chatBody = document.getElementById('chatBody');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.className = 'chat-message ai';
    typingDiv.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px;">AI Assistant</div>
      <div>Analyzing your request<span class="typing-dots"><span></span><span></span><span></span></span></div>
    `;
    chatBody.appendChild(typingDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function hideTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
  }

  function appendMsg(sender, message, modifications = [], suggestions = [], showGenerateButton = false) {
    const chatBody = document.getElementById('chatBody');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${sender}`;

    let modificationHtml = '';
    if (modifications.length > 0) {
      modificationHtml = `
        <div class="modifications-container">
          <div class="modifications-header">Proposed Changes:</div>
          ${modifications.map((mod, index) => `
            <div class="modification-item">
              <div class="modification-preview">
                <strong>${mod.type.toUpperCase().replace('_', ' ')}: ${mod.target}</strong>
                <p>${mod.preview}</p>
              </div>
              <div class="modification-actions">
                <button class="btn-apply" onclick="applyModification(${JSON.stringify(mod).replace(/"/g, '&quot;')}, ${index})">Apply Change</button>
                <button class="btn-skip" onclick="skipModification(${index})">Skip</button>
              </div>
            </div>
          `).join('')}
          <div class="bulk-actions">
            <button class="btn-apply-all" onclick="applyAllModifications(${JSON.stringify(modifications).replace(/"/g, '&quot;')})">Apply All</button>
            <button class="btn-skip-all" onclick="skipAllModifications()">Skip All</button>
          </div>
        </div>
      `;
    }

    // Suggestion cards HTML
    let suggestionsHtml = '';
    if (suggestions.length > 0) {
      suggestionsHtml = `
        <div class="suggestions-container">
          <div class="suggestions-header">Quick responses:</div>
          <div class="suggestions-grid">
            ${suggestions.map((suggestion, index) => `
              <button class="suggestion-card" onclick="selectSuggestion('${suggestion.replace(/'/g, "\\'")}')">
                ${suggestion}
              </button>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Generate button
    let generateButtonHtml = '';
    if (showGenerateButton) {
      const buttonText = conversationState.mode === 'modify' ? 'Apply Improvements' : 'Generate Comprehensive PRD';
      generateButtonHtml = `
        <div class="generate-button-container">
          <button class="btn-generate-specs" onclick="generateInitialSpecs()">
            🚀 ${buttonText}
          </button>
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px;">${sender === 'user' ? 'You' : 'AI Assistant'}</div>
      <div>${message}</div>
      ${modificationHtml}
      ${suggestionsHtml}
      ${generateButtonHtml}
    `;

    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  // Path Selection Handler
  function selectPath(pathType) {
    const chatBody = document.getElementById('chatBody');

    // Remove initial path selection
    const pathSelection = document.querySelector('.initial-path-selection');
    if (pathSelection) {
      pathSelection.remove();
    }

    // Add user's path selection to chat
    appendMsg('user', pathType === 'modify' ? 'I want to modify the current PRD' : 'I want to create a new PRD from an idea');

    // Set conversation mode
    conversationState.mode = pathType;
    conversationState.stage = 'initial';

    if (pathType === 'modify') {
      handleModifyPRDPath();
    } else {
      handleCreateNewPRDPath();
    }
  }

  async function handleModifyPRDPath() {
    try {
      // Get current PRD content for context
      const currentContent = await editor.save();

      // Analyze current PRD and suggest improvements
      showTyping();

      const response = await fetch('/api/prd-editor/analyze-current-prd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: currentContent,
          prd_id: currentPRDId
        })
      });

      hideTyping();

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          appendMsg('ai', data.data.message, [], data.data.suggestions || []);
        } else {
          appendMsg('ai', 'I can help you improve your current PRD. What specific aspect would you like to enhance?', [], [
            'Add more detailed user personas',
            'Improve technical specifications',
            'Add implementation timeline',
            'Enhance success metrics'
          ]);
        }
      } else {
        // Fallback if API not available
        appendMsg('ai', 'I can help you improve your current PRD. What specific aspect would you like to enhance?', [], [
          'Add more detailed user personas',
          'Improve technical specifications',
          'Add implementation timeline',
          'Enhance success metrics'
        ]);
      }
    } catch (error) {
      hideTyping();
      appendMsg('ai', 'I can help you improve your current PRD. What specific aspect would you like to enhance?', [], [
        'Add more detailed user personas',
        'Improve technical specifications',
        'Add implementation timeline',
        'Enhance success metrics'
      ]);
    }
  }

  async function handleCreateNewPRDPath() {
    // Start the drilling conversation for new PRD
    conversationState.mode = 'create';
    conversationState.history = [];
    conversationState.stage = 'gathering';

    appendMsg('ai', "Great! Let's create a comprehensive PRD for your new project. What's your idea?", [], [
      'A mobile app for...',
      'A web platform that...',
      'An AI-powered tool for...',
      'A SaaS solution for...'
    ]);
  }

  // Enhanced AI Chat Message Handler
  async function handleAiChatMessage(userMessage) {
    console.log('Processing message:', userMessage);

    // Check conversation mode
    if (conversationState.mode === 'modify') {
      return await handleModifyConversation(userMessage);
    } else if (conversationState.mode === 'create') {
      return await handleCreateConversation(userMessage);
    }

    // Default conversation handling
    try {
      const aiResponse = await callBackendAI(userMessage, null);

      if (aiResponse.stage && aiResponse.nextAction) {
        conversationState.stage = aiResponse.stage;
        if (aiResponse.conversationData) {
          Object.assign(conversationState, aiResponse.conversationData);
        }

        switch (aiResponse.nextAction) {
          case 'await_user_response':
            return {
              message: aiResponse.message,
              modifications: [],
              isConversational: true,
              stage: aiResponse.stage
            };
          case 'continue_conversation':
            return {
              message: aiResponse.message,
              modifications: [],
              isConversational: true,
              stage: aiResponse.stage,
              suggestions: aiResponse.suggestions || [],
              show_generate_button: aiResponse.show_generate_button || false
            };
          case 'await_confirmation':
            return {
              message: aiResponse.message,
              modifications: [],
              isConversational: true,
              stage: 'confirming'
            };
          case 'generate_prd':
            return await handlePRDGeneration(conversationState);
          default:
            return {
              message: aiResponse.message,
              modifications: aiResponse.suggestions || [],
              isConversational: false
            };
        }
      }

      if (aiResponse.suggestions) {
        return {
          message: aiResponse.message,
          modifications: aiResponse.suggestions.suggestions || [],
          isConversational: false
        };
      }

      return {
        message: aiResponse.message,
        modifications: [],
        isConversational: true,
        suggestions: aiResponse.suggestions || [],
        show_generate_button: aiResponse.show_generate_button || false
      };

    } catch (error) {
      console.error('Error in AI chat:', error);
      return {
        message: "I'm having trouble processing your request right now. Please try again.",
        modifications: [],
        isConversational: true
      };
    }
  }

  async function handleModifyConversation(userMessage) {
    try {
      // Use the same intelligent conversation system as create path
      // Add user message to conversation history
      if (!conversationState.history) {
        conversationState.history = [];
      }

      conversationState.history.push({
        role: 'user',
        message: userMessage,
        timestamp: new Date().toISOString()
      });

      // Use the same endpoint as create path but with modify context
      const response = await fetch('/api/prd-editor/simple-conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `MODIFY PRD CONTEXT: User wants to improve their existing PRD. USER REQUEST: "${userMessage}". Provide intelligent follow-up questions and specific suggestions for PRD enhancement.`,
          conversation_state: {
            ...conversationState,
            mode: 'modify'
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Update conversation state
          if (data.data.conversation_state) {
            Object.assign(conversationState, data.data.conversation_state);
          }

          // Check if we should show generate button (after 3+ exchanges)
          const showGenerateButton = conversationState.history && conversationState.history.length >= 6;

          return {
            message: data.data.message,
            modifications: [],
            isConversational: true,
            suggestions: data.data.suggestions || [],
            show_generate_button: showGenerateButton
          };
        }
      }

      // Enhanced fallback with specific suggestions
      return {
        message: "I can help you enhance your PRD! What specific aspect would you like to improve?",
        modifications: [],
        isConversational: true,
        suggestions: [
          "Add detailed user personas and user journeys",
          "Enhance technical architecture with diagrams",
          "Improve functional requirements with specific use cases",
          "Add comprehensive implementation timeline and phases"
        ]
      };

    } catch (error) {
      console.error('Error in modify conversation:', error);
      return {
        message: "I can help you enhance your PRD! What specific aspect would you like to improve?",
        modifications: [],
        isConversational: true,
        suggestions: [
          "Add detailed user personas and user journeys",
          "Enhance technical architecture with diagrams",
          "Improve functional requirements with specific use cases",
          "Add comprehensive implementation timeline and phases"
        ]
      };
    }
  }

  async function handleCreateConversation(userMessage) {
    try {
      // Add user message to conversation history
      if (!conversationState.history) {
        conversationState.history = [];
      }

      conversationState.history.push({
        role: 'user',
        message: userMessage,
        timestamp: new Date().toISOString()
      });

      // Use the existing simple-conversation endpoint
      const response = await fetch('/api/prd-editor/simple-conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_state: conversationState
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Update conversation state
          if (data.data.conversation_state) {
            Object.assign(conversationState, data.data.conversation_state);
          }

          // Add AI response to history
          conversationState.history.push({
            role: 'assistant',
            message: data.data.message,
            timestamp: new Date().toISOString()
          });

          // Check if we should show generate button (after 3+ exchanges)
          const showGenerateButton = conversationState.history.length >= 6;

          return {
            message: data.data.message,
            modifications: [],
            isConversational: true,
            suggestions: data.data.suggestions || [],
            show_generate_button: showGenerateButton || data.data.show_generate_button
          };
        }
      }

      // Fallback
      return {
        message: "Tell me more about your project idea. What problem are you trying to solve?",
        modifications: [],
        isConversational: true
      };

    } catch (error) {
      console.error('Error in create conversation:', error);
      return {
        message: "I'm having trouble processing your request. Please try again.",
        modifications: [],
        isConversational: true
      };
    }
  }


  // Handle PRD Generation from conversation data
  async function handlePRDGeneration(conversationData) {
    try {
      const projectType = conversationData.context?.projectType || 'unknown';
      const responses = conversationData.context?.responses || {};

      // Generate comprehensive PRD using the backend
      const prdData = await generateComprehensivePRD(responses, projectType, currentProjectId);

      if (prdData && prdData.editorjs_content) {
        // Apply the generated content to the editor
        if (editor) {
          await editor.render(prdData.editorjs_content);
        }

        return {
          message: `🎉 I've generated a comprehensive PRD for your ${projectType} project! The document includes all the sections we discussed, including architecture diagrams, user stories, and technical requirements. You can now review and edit the content as needed.`,
          modifications: [],
          isConversational: false,
          prdGenerated: true
        };
      } else {
        throw new Error('Failed to generate PRD content');
      }
    } catch (error) {
      console.error('Error generating PRD:', error);
      return {
        message: "I encountered an issue generating the PRD. Let me provide you with a summary of what we discussed instead, and you can use that to create the document manually.",
        modifications: [],
        isConversational: false
      };
    }
  }

  function isDocumentCreationRequest(message) {
    const creationKeywords = [
      'create prd', 'build prd', 'generate prd', 'new prd',
      'create trd', 'build trd', 'generate trd', 'new trd',
      'create product requirements', 'build product requirements',
      'create technical requirements', 'build technical requirements',
      'build system', 'create system', 'develop application',
      'build app', 'create app', 'new project', 'new system'
    ];

    return creationKeywords.some(keyword => message.includes(keyword));
  }

  async function startComprehensiveInterview(userMessage) {
    try {
      // Call the backend to get the first comprehensive question
      const backendResponse = await callBackendAI(userMessage);

      // Initialize conversation state based on backend response
      conversationState = {
        stage: 'gathering',
        context: {
          initialRequest: userMessage,
          projectType: backendResponse.conversationData?.project_type || 'Software System',
          responses: {}
        },
        questionHistory: [],
        currentTopic: backendResponse.conversationData?.current_topic || 'overview',
        documentsToGenerate: ['prd']
      };

      conversationState.questionHistory.push({
        question: backendResponse.message,
        topic: conversationState.currentTopic,
        timestamp: new Date()
      });

      return {
        message: backendResponse.message,
        modifications: [],
        isConversational: true,
        stage: 'gathering'
      };
    } catch (error) {
      console.error('Error starting comprehensive interview:', error);

      // Fallback to frontend logic
      conversationState = {
        stage: 'gathering',
        context: {
          initialRequest: userMessage,
          projectType: detectProjectType(userMessage),
          responses: {}
        },
        questionHistory: [],
        currentTopic: 'overview',
        documentsToGenerate: ['prd']
      };

      const projectType = conversationState.context.projectType;
      const firstQuestion = getInitialQuestion(projectType, userMessage);

      conversationState.questionHistory.push({
        question: firstQuestion,
        topic: 'overview',
        timestamp: new Date()
      });

      return {
        message: `I'll help you create a comprehensive ${projectType} specification. Let me ask you some detailed questions to ensure we build exactly what you need.\n\n${firstQuestion}`,
        modifications: [],
        isConversational: true,
        stage: 'gathering'
      };
    }
  }

  function detectProjectType(message) {
    const message_lower = message.toLowerCase();

    if (message_lower.includes('ai') || message_lower.includes('machine learning') || message_lower.includes('ml')) {
      return 'AI/ML System';
    } else if (message_lower.includes('api') || message_lower.includes('backend') || message_lower.includes('service')) {
      return 'Backend Service';
    } else if (message_lower.includes('web') || message_lower.includes('frontend') || message_lower.includes('ui')) {
      return 'Web Application';
    } else if (message_lower.includes('mobile') || message_lower.includes('app')) {
      return 'Mobile Application';
    } else if (message_lower.includes('platform') || message_lower.includes('infrastructure')) {
      return 'Platform/Infrastructure';
    } else if (message_lower.includes('analytics') || message_lower.includes('dashboard') || message_lower.includes('reporting')) {
      return 'Analytics Platform';
    } else {
      return 'Software System';
    }
  }

  function getInitialQuestion(projectType, userMessage) {
    const questions = {
      'AI/ML System': `What specific AI/ML problem are you trying to solve? Please describe:
      
1. What type of data will you be working with?
2. What kind of predictions or insights do you want to generate?
3. Who will be using this system and how?
4. What's the current manual process you're trying to automate or improve?`,

      'Backend Service': `Let me understand your backend service requirements:
      
1. What specific business problem does this service solve?
2. What are the main operations/functions it needs to perform?
3. What other systems or services will it integrate with?
4. What's your expected scale (users, requests per second, data volume)?`,

      'Web Application': `I need to understand your web application vision:
      
1. What's the main purpose and value proposition of this application?
2. Who are your target users (roles, technical level, use cases)?
3. What are the core workflows users will follow?
4. Do you have any existing systems this needs to integrate with?`,

      'Mobile Application': `Tell me about your mobile application concept:
      
1. What problem does this app solve for users?
2. Is this iOS, Android, or cross-platform?
3. What are the main user journeys and features?
4. Will it need backend services or work offline?`,

      'Platform/Infrastructure': `Help me understand your platform requirements:
      
1. What services or capabilities will this platform provide?
2. Who are the internal/external users of this platform?
3. What's the current infrastructure landscape you're working with?
4. What are your scalability and reliability requirements?`,

      'Analytics Platform': `Let's define your analytics platform:
      
1. What data sources will you be analyzing?
2. What types of insights or reports do stakeholders need?
3. Who will be the primary users (analysts, executives, engineers)?
4. What's your data volume and real-time requirements?`,

      'Software System': `Let me understand what you want to build:
      
1. What's the main business problem this system will solve?
2. Who will use this system and how?
3. What are the key functions or capabilities needed?
4. Are there any existing systems or constraints I should know about?`
    };

    return questions[projectType] || questions['Software System'];
  }

  async function handleGatheringStage(userMessage) {
    // Store the user's response
    const currentTopic = conversationState.currentTopic;
    conversationState.context.responses[currentTopic] = userMessage;

    // Determine next question based on conversation flow
    const nextQuestion = await getNextDrillingQuestion(userMessage, currentTopic);

    if (nextQuestion.isComplete) {
      // Move to confirmation stage
      conversationState.stage = 'confirming';
      return await generateConfirmationSummary();
    } else {
      // Continue gathering information
      conversationState.currentTopic = nextQuestion.topic;
      conversationState.questionHistory.push({
        question: nextQuestion.question,
        topic: nextQuestion.topic,
        timestamp: new Date()
      });

      return {
        message: nextQuestion.question,
        modifications: [],
        isConversational: true,
        stage: 'gathering'
      };
    }
  }

  async function getNextDrillingQuestion(userResponse, currentTopic) {
    const responses = conversationState.context.responses;

    // Define the comprehensive question flow
    const questionFlow = {
      'overview': () => {
        if (!responses.users) {
          return {
            topic: 'users',
            question: `Great! Now let's dive deeper into your users. Based on what you described, I need to understand:

1. What are the different types of users (roles/personas) who will interact with this system?
2. What are their specific needs, pain points, and goals?
3. What's their technical expertise level?
4. How do they currently solve this problem (if at all)?
5. What would success look like for each type of user?`
          };
        }
        return { isComplete: true };
      },

      'users': () => {
        if (!responses.technical_requirements) {
          return {
            topic: 'technical_requirements',
            question: `Perfect! Now let's get into the technical details:

1. What's your preferred technology stack (if any)?
2. What are your performance requirements (response times, throughput)?
3. What are your scalability needs (concurrent users, data volume)?
4. Do you have any security or compliance requirements?
5. What's your deployment environment (cloud, on-premise, hybrid)?
6. Are there any integration requirements with existing systems?`
          };
        }
        return { isComplete: true };
      },

      'technical_requirements': () => {
        if (!responses.business_requirements) {
          return {
            topic: 'business_requirements',
            question: `Now let's cover the business aspects:

1. What are your success metrics and KPIs?
2. What's your timeline and any critical milestones?
3. What's your budget range or resource constraints?
4. Who are the key stakeholders and decision makers?
5. What are the biggest risks or concerns you have?
6. Are there any regulatory or compliance requirements?`
          };
        }
        return { isComplete: true };
      },

      'business_requirements': () => {
        if (!responses.functional_details) {
          return {
            topic: 'functional_details',
            question: `Let's get specific about functionality:

1. What are the core features that are absolutely essential (MVP)?
2. What are nice-to-have features for future versions?
3. Can you walk me through the main user workflows step-by-step?
4. What data will the system need to store and process?
5. What are the key business rules and logic?
6. Are there any specific UI/UX requirements or preferences?`
          };
        }
        return { isComplete: true };
      },

      'functional_details': () => {
        if (!responses.non_functional) {
          return {
            topic: 'non_functional',
            question: `Finally, let's cover non-functional requirements:

1. What are your availability requirements (uptime, maintenance windows)?
2. What are your disaster recovery and backup needs?
3. How will you handle monitoring, logging, and observability?
4. What are your testing and quality assurance requirements?
5. Do you need multi-language or accessibility support?
6. What about data retention and privacy requirements?`
          };
        }
        return { isComplete: true };
      }
    };

    const nextQuestionFunc = questionFlow[currentTopic];
    if (nextQuestionFunc) {
      return nextQuestionFunc();
    }

    return { isComplete: true };
  }

  async function generateConfirmationSummary() {
    const responses = conversationState.context.responses;
    const projectType = conversationState.context.projectType;

    const summary = `## Summary of Your ${projectType} Requirements

Based on our conversation, here's what I understand:

**Project Overview:**
${responses.overview || 'Not specified'}

**Target Users & Personas:**
${responses.users || 'Not specified'}

**Technical Requirements:**
${responses.technical_requirements || 'Not specified'}

**Business Requirements:**
${responses.business_requirements || 'Not specified'}

**Functional Details:**
${responses.functional_details || 'Not specified'}

**Non-Functional Requirements:**
${responses.non_functional || 'Not specified'}

---

Does this summary accurately capture your requirements? If yes, I'll generate a comprehensive PRD, TRD, and other relevant documents. If you'd like to modify or add anything, please let me know what needs to be changed.`;

    return {
      message: summary,
      modifications: [{
        type: 'generate_documents',
        target: 'Comprehensive Documentation',
        preview: 'Generate PRD, TRD, and supporting documents based on the gathered requirements',
        data: {
          projectType,
          responses,
          documentsToGenerate: ['prd', 'trd', 'user_stories', 'technical_architecture']
        }
      }],
      isConversational: true,
      stage: 'confirming'
    };
  }

  async function handleConfirmingStage(userMessage) {
    const message = userMessage.toLowerCase();

    if (message.includes('yes') || message.includes('correct') || message.includes('accurate') || message.includes('generate')) {
      conversationState.stage = 'generating';
      return await generateComprehensiveDocuments();
    } else {
      // User wants to modify something - ask what to change
      return {
        message: "What would you like to modify or add to the requirements? Please be specific about which section needs changes.",
        modifications: [],
        isConversational: true,
        stage: 'confirming'
      };
    }
  }

  async function generateComprehensiveDocuments() {
    const responses = conversationState.context.responses;
    const projectType = conversationState.context.projectType;

    try {
      // Call the backend AI service to generate documents
      const documentGeneration = await callBackendForDocumentGeneration(responses, projectType);

      return {
        message: "Perfect! I'm generating your comprehensive documentation now. This includes:\n\n• **Product Requirements Document (PRD)**\n• **Technical Requirements Document (TRD)**\n• **User Stories & Use Cases**\n• **System Architecture Overview**\n• **Implementation Plan**\n\nThis will take a moment...",
        modifications: [{
          type: 'generate_comprehensive_docs',
          target: 'Complete Documentation Suite',
          preview: 'Generate and insert comprehensive PRD, TRD, and supporting documents',
          data: documentGeneration
        }],
        isConversational: false,
        stage: 'generating'
      };
    } catch (error) {
      console.error('Error generating documents:', error);
      return {
        message: "I encountered an issue generating the documents. Let me create a structured outline based on our conversation instead.",
        modifications: [{
          type: 'generate_outline',
          target: 'Requirements Outline',
          preview: 'Create a structured outline based on the gathered requirements',
          data: { responses, projectType }
        }],
        isConversational: false,
        stage: 'complete'
      };
    }
  }

  async function callBackendForDocumentGeneration(responses, projectType) {
    // Construct comprehensive prompt for document generation
    const comprehensivePrompt = buildComprehensivePrompt(responses, projectType);

    try {
      // Use the existing Model Garden API
      const response = await fetch('/api/model-garden/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          instruction: comprehensivePrompt,
          model: 'claude-opus-4',
          role: 'po'
        })
      });

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        return {
          prdContent: result.output,
          projectType: projectType,
          responses: responses
        };
      } else {
        throw new Error(result.error || 'Failed to generate documents');
      }
    } catch (error) {
      console.error('Backend API call failed:', error);
      throw error;
    }
  }

  // Enhanced backend integration with new comprehensive AI endpoints
  async function callBackendAI(message, prdId = null) {
    try {
      // Use comprehensive conversation endpoint for drilling conversations
      if (conversationState.stage === 'gathering' || conversationState.stage === 'initial') {
        const response = await fetch('/api/prd-editor/simple-conversation', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: message,
            conversation_state: conversationState,
            project_id: currentProjectId
          })
        });

        if (!response.ok) {
          throw new Error(`Comprehensive conversation failed: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
          // Parse the AI response if it's JSON wrapped in a string
          let aiResponse = result.data;
          if (typeof result.data.message === 'string' && result.data.message.startsWith('```json')) {
            try {
              const jsonStr = result.data.message.replace(/```json\n?/, '').replace(/```$/, '');
              aiResponse = JSON.parse(jsonStr);
            } catch (e) {
              console.warn('Failed to parse JSON from AI response, using as-is');
            }
          }

          // Update conversation state
          if (aiResponse.conversation_state) {
            Object.assign(conversationState, aiResponse.conversation_state);
          }

          return {
            message: aiResponse.message,
            stage: aiResponse.stage,
            nextAction: aiResponse.next_action,
            suggestions: result.data.suggestions || [],
            show_generate_button: result.data.show_generate_button || false,
            conversationData: aiResponse.conversation_state,
            aiMetadata: result.data.ai_metadata
          };
        } else {
          throw new Error(result.error || 'Failed to get comprehensive conversation response');
        }
      }

      // Use PRD Editor AI enhancement endpoint if we have a PRD ID
      if (prdId) {
        const response = await fetch(`/api/prd-editor/prds/${prdId}/ai-enhance`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            request: message,
            editorjs_content: getCurrentEditorContent()
          })
        });

        if (!response.ok) {
          throw new Error(`PRD AI enhancement failed: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
          return {
            message: result.data.suggestions.summary || 'AI suggestions generated',
            suggestions: result.data.suggestions,
            conversationData: null,
            aiMetadata: result.data.ai_metadata
          };
        } else {
          throw new Error(result.error || 'Failed to get AI enhancement');
        }
      }

      // Fall back to model garden for other requests
      const response = await fetch('/api/model-garden/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          instruction: message,
          model: 'claude-opus-4',
          role: 'po'
        })
      });

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        return {
          message: result.output,
          conversationData: result.conversation_data || null
        };
      } else {
        throw new Error(result.error || 'Failed to get AI response');
      }
    } catch (error) {
      console.error('Backend AI call failed:', error);
      throw error;
    }
  }

  // Generate comprehensive PRD from conversation data
  async function generateComprehensivePRD(conversationData, projectType, projectId = null) {
    try {
      const response = await fetch('/api/prd-editor/generate-comprehensive-prd', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          conversation_data: conversationData,
          project_type: projectType,
          project_id: projectId
        })
      });

      if (!response.ok) {
        throw new Error(`PRD generation failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        console.log('Comprehensive PRD generated:', result.data);
        return result.data;
      } else {
        throw new Error(result.error || 'Failed to generate comprehensive PRD');
      }
    } catch (error) {
      console.error('Error generating comprehensive PRD:', error);
      throw error;
    }
  }

  // Generate specific PRD section
  async function generatePRDSection(sectionType, contextData, projectType) {
    try {
      const response = await fetch('/api/prd-editor/generate-section', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          section_type: sectionType,
          context_data: contextData,
          project_type: projectType
        })
      });

      if (!response.ok) {
        throw new Error(`Section generation failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        console.log(`Section '${sectionType}' generated:`, result.data);
        return result.data;
      } else {
        throw new Error(result.error || 'Failed to generate section');
      }
    } catch (error) {
      console.error(`Error generating section '${sectionType}':`, error);
      throw error;
    }
  }

  // Get current Editor.js content (placeholder - will be implemented when Editor.js is integrated)
  function getCurrentEditorContent() {
    // TODO: Implement when Editor.js is properly integrated
    return {
      time: Date.now(),
      blocks: [],
      version: "2.28.2"
    };
  }

  // Save PRD content to backend
  async function savePRDContent(prdId, editorjsContent) {
    try {
      const response = await fetch(`/api/prd-editor/prds/${prdId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          editorjs_content: editorjsContent
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to save PRD: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        console.log('PRD saved successfully:', result.data);
        return result.data;
      } else {
        throw new Error(result.error || 'Failed to save PRD');
      }
    } catch (error) {
      console.error('Error saving PRD:', error);
      throw error;
    }
  }

  // Create PRD from FeedItem (Think → Define integration)
  async function createPRDFromFeedItem(feedItemId, createdBy = 'editor-user') {
    try {
      const response = await fetch(`/api/prd-editor/feed-items/${feedItemId}/create-prd`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          created_by: createdBy
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create PRD from feed item: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        console.log('PRD created from feed item:', result.data);
        return result.data;
      } else {
        throw new Error(result.error || 'Failed to create PRD from feed item');
      }
    } catch (error) {
      console.error('Error creating PRD from feed item:', error);
      throw error;
    }
  }

  function buildComprehensivePrompt(responses, projectType) {
    return `You are a senior product manager and business analyst. Based on the following comprehensive requirements gathering session, create a detailed Product Requirements Document (PRD) and Technical Requirements Document (TRD).

PROJECT TYPE: ${projectType}

GATHERED REQUIREMENTS:
${Object.entries(responses).map(([topic, response]) => `
**${topic.toUpperCase().replace('_', ' ')}:**
${response}
`).join('\n')}

Please generate a comprehensive PRD that includes:

1. **Executive Summary** - Clear overview of the project
2. **Problem Statement** - What problem we're solving and why
3. **Target Users & Personas** - Detailed user profiles with needs and pain points
4. **User Stories & Use Cases** - Specific scenarios and workflows
5. **Functional Requirements** - What the system must do
6. **Non-Functional Requirements** - Performance, security, scalability
7. **Technical Architecture** - High-level system design
8. **Success Metrics** - How we'll measure success
9. **Implementation Plan** - Phases and milestones
10. **Risks & Mitigations** - Potential issues and solutions

Format the output as clean, professional markdown that can be directly inserted into a PRD document. Use clear headings, bullet points, and structured content. Include specific details from the requirements gathering session.

Make it comprehensive like the example you've seen - ask clarifying questions within the document where more details might be needed, and provide specific, actionable requirements rather than vague statements.`;
  }

  async function handleEnhancementRequests(userMessage) {
    // Handle the original enhancement functionality for existing PRDs
    const message = userMessage.toLowerCase();

    // Analyze user intent and generate appropriate modifications
    const modifications = [];
    let responseMessage = "I understand you want to enhance your PRD. ";

    if (message.includes('add') && message.includes('section')) {
      modifications.push({
        type: 'add_section',
        target: 'New Section',
        preview: 'Add a new section with title and content placeholder',
        data: {
          title: extractSectionTitle(userMessage) || 'New Section',
          content: '<p>Content will be generated here...</p>'
        }
      });
      responseMessage += "I'll add a new section to your PRD.";
    }

    if (message.includes('enhance') || message.includes('improve')) {
      const currentBlocks = await editor.save();
      if (currentBlocks.blocks.length > 0) {
        modifications.push({
          type: 'enhance_content',
          target: 'Current Section',
          preview: 'Enhance existing content with more details and structure',
          data: {
            blockIndex: 0, // Target first block for demo
            enhancement: 'Enhanced with additional details, examples, and improved structure.'
          }
        });
        responseMessage += "I'll enhance your existing content with more details.";
      }
    }

    if (message.includes('diagram') || message.includes('mermaid')) {
      const diagramType = extractDiagramType(userMessage);
      modifications.push({
        type: 'add_diagram',
        target: `${diagramType} Diagram`,
        preview: `Add a ${diagramType} diagram with relevant content`,
        data: {
          diagramType,
          code: generateDiagramCode(diagramType)
        }
      });
      responseMessage += `I'll add a ${diagramType} diagram to illustrate the concepts.`;
    }

    if (message.includes('user stories') || message.includes('requirements')) {
      modifications.push({
        type: 'add_requirements',
        target: 'User Stories & Requirements',
        preview: 'Add structured user stories and functional requirements',
        data: {
          content: generateRequirementsContent()
        }
      });
      responseMessage += "I'll add structured user stories and requirements.";
    }

    if (modifications.length === 0) {
      // Fallback: suggest general improvements
      modifications.push({
        type: 'general_suggestion',
        target: 'Content Enhancement',
        preview: 'Add a comprehensive section based on your request',
        data: {
          content: `<p>Based on your request: "${userMessage}"</p><p>I suggest adding more structured content here with relevant details.</p>`
        }
      });
      responseMessage += "I'll add some relevant content based on your request.";
    }

    return {
      message: responseMessage,
      modifications
    };
  }

  // Apply a modification to the editor
  async function applyModification(modification) {
    try {
      switch (modification.type) {
        case 'add_section':
          await editor.blocks.insert('section', {
            title: modification.data.title,
            html: modification.data.content,
            collapsed: false
          });
          break;

        case 'enhance_content':
          const blocks = await editor.save();
          if (blocks.blocks[modification.data.blockIndex]) {
            const block = blocks.blocks[modification.data.blockIndex];
            if (block.type === 'section') {
              const enhanced = block.data.html + '<p>' + modification.data.enhancement + '</p>';
              await editor.blocks.update(modification.data.blockIndex, {
                ...block.data,
                html: enhanced
              });
            }
          }
          break;

        case 'add_diagram':
          await editor.blocks.insert('mermaid', {
            code: modification.data.code
          });
          // Trigger mermaid rendering after a short delay
          setTimeout(renderAllMermaidDiagrams, 300);
          break;

        case 'add_requirements':
          await editor.blocks.insert('section', {
            title: 'User Stories & Requirements',
            html: modification.data.content,
            collapsed: false
          });
          break;

        case 'general_suggestion':
          await editor.blocks.insert('section', {
            title: 'AI Suggestion',
            html: modification.data.content,
            collapsed: false
          });
          break;

        case 'generate_comprehensive_docs':
          await generateAndInsertComprehensiveDocs(modification.data);
          break;

        case 'generate_outline':
          await generateAndInsertOutline(modification.data);
          break;
      }

      // Update outline after modifications
      setTimeout(buildOutline, 200);

    } catch (error) {
      console.error('Failed to apply modification:', error);
      throw error;
    }
  }

  async function generateAndInsertComprehensiveDocs(data) {
    try {
      // Clear existing content
      await editor.clear();

      // Parse the generated PRD content and insert as blocks
      const content = data.prdContent;
      const lines = content.split('\n');

      for (const line of lines) {
        if (line.startsWith('#')) {
          // Header
          const level = (line.match(/#/g) || []).length;
          const text = line.replace(/#/g, '').trim();
          if (text) {
            await editor.blocks.insert('header', {
              text: text,
              level: Math.min(level, 6)
            });
          }
        } else if (line.trim() && !line.startsWith('-') && !line.startsWith('*')) {
          // Paragraph
          await editor.blocks.insert('paragraph', {
            text: line.trim()
          });
        } else if (line.startsWith('-') || line.startsWith('*')) {
          // List item - collect consecutive items
          const listItems = [line.substring(1).trim()];
          // This is a simplified approach - in practice you'd want to collect all consecutive list items
          await editor.blocks.insert('list', {
            style: 'unordered',
            items: listItems
          });
        }
      }

      // Update outline
      setTimeout(buildOutline, 500);

    } catch (error) {
      console.error('Error generating comprehensive docs:', error);
      // Fallback: insert as a single section
      await editor.blocks.insert('section', {
        title: `${data.projectType} Requirements`,
        html: `<pre>${data.prdContent}</pre>`
      });
    }
  }

  async function generateAndInsertOutline(data) {
    const { responses, projectType } = data;

    const outlineContent = `
      <h3>Project Overview</h3>
      <p><strong>Type:</strong> ${projectType}</p>
      <p><strong>Initial Request:</strong> ${responses.overview || 'Not specified'}</p>
      
      <h3>Key Requirements Gathered</h3>
      <ul>
        <li><strong>Users & Personas:</strong> ${responses.users || 'To be defined'}</li>
        <li><strong>Technical Requirements:</strong> ${responses.technical_requirements || 'To be defined'}</li>
        <li><strong>Business Requirements:</strong> ${responses.business_requirements || 'To be defined'}</li>
        <li><strong>Functional Details:</strong> ${responses.functional_details || 'To be defined'}</li>
        <li><strong>Non-Functional Requirements:</strong> ${responses.non_functional || 'To be defined'}</li>
      </ul>
      
      <h3>Next Steps</h3>
      <p>Complete the requirements gathering process and generate comprehensive PRD/TRD documents.</p>
    `;

    await editor.blocks.insert('section', {
      title: 'Requirements Outline',
      html: outlineContent,
      collapsed: false
    });
  }

  // Helper functions for content generation
  function extractSectionTitle(message) {
    const patterns = [
      /add.*section.*["'](.*?)["']/i,
      /add.*["'](.*?)["'].*section/i,
      /section.*["'](.*?)["']/i
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) return match[1];
    }

    return null;
  }

  function extractDiagramType(message) {
    const msg = message.toLowerCase();
    if (msg.includes('flowchart') || msg.includes('flow')) return 'flowchart';
    if (msg.includes('erd') || msg.includes('entity')) return 'er';
    if (msg.includes('class') || msg.includes('uml')) return 'class';
    if (msg.includes('sequence')) return 'sequence';
    return 'flowchart'; // default
  }

  function generateDiagramCode(type) {
    const templates = {
      flowchart: `flowchart TD
    A[User Request] --> B{Analyze Intent}
    B -->|Add Content| C[Generate Section]
    B -->|Enhance| D[Improve Existing]
    C --> E[Apply Changes]
    D --> E
    E --> F[Update PRD]`,
      er: `erDiagram
    PRD ||--o{ SECTION : contains
    SECTION ||--o{ REQUIREMENT : includes
    SECTION ||--o{ USER_STORY : defines
    REQUIREMENT ||--o{ ACCEPTANCE_CRITERIA : has`,
      class: `classDiagram
    class PRDEditor {
        +addSection()
        +enhanceContent()
        +generateDiagram()
    }
    class AIAssistant {
        +analyzeIntent()
        +generateModifications()
    }
    PRDEditor --> AIAssistant`,
      sequence: `sequenceDiagram
    participant U as User
    participant AI as AI Assistant
    participant E as Editor
    U->>AI: Request enhancement
    AI->>AI: Analyze intent
    AI->>U: Propose modifications
    U->>AI: Approve changes
    AI->>E: Apply modifications
    E->>U: Updated PRD`
    };

    return templates[type] || templates.flowchart;
  }

  function generateRequirementsContent() {
    return `
      <h4>User Stories</h4>
      <div class="user-story" style="background:#f0fdf4;border-left:4px solid #22c55e;padding:12px;margin:8px 0;border-radius:0 8px 8px 0;">
        <strong>As a</strong> Product Owner, <strong>I want</strong> to create comprehensive PRDs, <strong>so that</strong> development teams have clear requirements.
      </div>
      <div class="user-story" style="background:#f0fdf4;border-left:4px solid #22c55e;padding:12px;margin:8px 0;border-radius:0 8px 8px 0;">
        <strong>As a</strong> Developer, <strong>I want</strong> detailed technical specifications, <strong>so that</strong> I can implement features correctly.
      </div>
      
      <h4>Functional Requirements</h4>
      <ul>
        <li>The system must support real-time collaborative editing</li>
        <li>Users must be able to export PRDs in multiple formats</li>
        <li>The system must provide AI-powered content suggestions</li>
        <li>All changes must be tracked with version history</li>
      </ul>
      
      <h4>Acceptance Criteria</h4>
      <ol>
        <li>User can create a new PRD within 30 seconds</li>
        <li>AI suggestions appear within 2 seconds of request</li>
        <li>Export functionality supports PDF, Markdown, and HTML formats</li>
        <li>System maintains 99.9% uptime during business hours</li>
      </ol>
    `;
  }

  // No mock/sample content. Editor requires real PRD content loaded from backend.

  // Initialize everything when DOM is loaded
  document.addEventListener('DOMContentLoaded', function () {
    // Initialize Mermaid
    if (window.mermaid && typeof mermaid.initialize === 'function') {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true
        }
      });
    } else {
      console.warn('Mermaid not loaded; diagrams disabled');
    }

    // Ensure EditorJS tools are ready before initializing
    waitForEditorJSTools().then(() => {
      initializeEditor();
      return editor.isReady;
    }).then(() => {
      loadPRDContent();
    }).catch((err) => {
      console.error('Failed to initialize EditorJS tools:', err);
      // Graceful fallback: show a user-friendly message in the editor area
      const container = document.getElementById('editorjs');
      if (container) {
        container.innerHTML = '<div style="padding:16px;border:1px solid #e2e8f0;border-radius:8px;background:#fff7ed;color:#9a3412;">Failed to load editor tools. Please check network connectivity or browser extensions blocking CDN scripts, then reload.</div>';
      }
    });

    // Setup chat functionality
    const sendBtn = document.getElementById('chatSend');
    const textEl = document.getElementById('chatInput');

    sendBtn?.addEventListener('click', async () => {
      const text = (textEl?.value || '').trim();
      if (!text) return;
      appendMsg('user', text);
      if (textEl) textEl.value = '';
      showTyping();

      try {
        const response = await handleAiChatMessage(text);
        hideTyping();

        if (response.modifications && response.modifications.length > 0) {
          // Show message with modifications
          appendMsg('ai', response.message, response.modifications);
        } else {
          // Show message with suggestions and generate button
          const suggestions = response.suggestions || [];
          const showGenerateButton = response.show_generate_button || false;
          appendMsg('ai', response.message, [], suggestions, showGenerateButton);
        }
      } catch (error) {
        hideTyping();
        appendMsg('ai', 'I encountered an error processing your request. Please try again.');
        console.error('AI chat error:', error);
      }
    });

    // Enter key support
    textEl?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendBtn?.click();
      }
    });

    // Restore chat open state
    if (isChatOpen) {
      ensureResizeHandle();
      updateChatLayout();
      document.body.classList.add('split-chat-open');
      const chatPanel = document.getElementById('aiChatPanel');
      if (chatPanel) chatPanel.classList.add('open');
      const handle = document.getElementById('chatResizeHandle');
      if (handle) handle.style.display = 'block';
      const chatBubble = document.querySelector('.ai-bubble');
      if (chatBubble) chatBubble.style.display = 'none';
    }
  });

  // Make functions globally available for HTML onclick handlers
  window.toggleAiChat = toggleAiChat;
  // Expose updateChatLayout if needed externally
  window.updateChatLayout = updateChatLayout;

  // Expose export and export dialog helpers for HTML buttons
  window.exportDocument = exportDocument;
  window.showExportDialog = showExportDialog;
  window.performExport = performExport;
  window.closeExportDialog = closeExportDialog;

  // Add sendChatMessage function for HTML onclick compatibility
  window.sendChatMessage = async function () {
    const textEl = document.getElementById('chatInput');
    const text = (textEl?.value || '').trim();
    if (!text) return;

    appendMsg('user', text);
    if (textEl) textEl.value = '';
    showTyping();

    try {
      const response = await handleAiChatMessage(text);
      hideTyping();

      if (response.modifications && response.modifications.length > 0) {
        // Show message with modifications
        appendMsg('ai', response.message, response.modifications, response.suggestions || [], response.show_generate_button || false);
      } else {
        // Simple response without modifications
        appendMsg('ai', response.message, [], response.suggestions || [], response.show_generate_button || false);
      }
    } catch (error) {
      hideTyping();
      appendMsg('ai', 'I encountered an error processing your request. Please try again.');
      console.error('AI chat error:', error);
    }
  };
  window.applyModification = async (modification, index) => {
    try {
      await applyModification(modification);
      // Update button to show applied state
      const button = document.querySelector(`[onclick*="applyModification"][onclick*="${index}"]`);
      if (button) {
        button.textContent = 'Applied ✓';
        button.disabled = true;
        button.style.background = '#22c55e';
      }
    } catch (error) {
      console.error('Failed to apply modification:', error);
    }
  };

  window.skipModification = (index) => {
    const button = document.querySelector(`[onclick*="skipModification"][onclick*="${index}"]`);
    if (button) {
      button.textContent = 'Skipped';
      button.disabled = true;
      button.style.background = '#6b7280';
    }
  };

  // Real-time Collaboration Functions

  window.initializeWebSocketConnection = function (prdId, projectId, userId = 'anonymous') {
    if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
      websocketConnection.close();
    }

    currentPRDId = prdId;
    currentProjectId = projectId;

    // Connect to WebSocket server
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    websocketConnection = new WebSocket(wsUrl);

    websocketConnection.onopen = function (event) {
      console.log('WebSocket connected for PRD collaboration');
      collaborationState.isConnected = true;

      // Join PRD-specific room
      const joinMessage = {
        type: 'join_room',
        room: `prd_${prdId}`,
        user_id: userId,
        project_id: projectId
      };
      websocketConnection.send(JSON.stringify(joinMessage));

      showNotification('Connected to collaborative editing');
    };

    websocketConnection.onmessage = function (event) {
      try {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    websocketConnection.onclose = function (event) {
      console.log('WebSocket disconnected');
      collaborationState.isConnected = false;

      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        if (currentPRDId) {
          initializeWebSocketConnection(currentPRDId, currentProjectId, userId);
        }
      }, 5000);
    };

    websocketConnection.onerror = function (error) {
      console.error('WebSocket error:', error);
      collaborationState.isConnected = false;
    };
  };

  function handleWebSocketMessage(message) {
    switch (message.type) {
      case 'user_joined':
        showNotification(`${message.data.user_name || message.data.user_id} joined the document`);
        break;
      case 'user_left':
        showNotification(`${message.data.user_name || message.data.user_id} left the document`);
        break;
      case 'content_changed':
        if (message.data.user_id !== getCurrentUserId()) {
          showNotification(`Content updated by ${message.data.user_name || message.data.user_id}`);
        }
        break;
      case 'prd_updated':
        if (message.data.status_change) {
          showNotification(`PRD status changed to: ${message.data.new_status}`);
        }
        break;
      default:
        console.log('WebSocket message:', message.type);
    }
  }

  function broadcastContentChange(changeType, content) {
    if (!websocketConnection || websocketConnection.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = {
      type: 'content_change',
      prd_id: currentPRDId,
      project_id: currentProjectId,
      user_id: getCurrentUserId(),
      change_type: changeType,
      content: content,
      timestamp: Date.now()
    };

    websocketConnection.send(JSON.stringify(message));
  }

  async function broadcastCollaborationEvent(eventData) {
    if (!currentPRDId) return;

    try {
      await fetch(`/api/prd-editor/prds/${currentPRDId}/collaborate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event: eventData,
          user_id: getCurrentUserId()
        })
      });
    } catch (error) {
      console.error('Error broadcasting collaboration event:', error);
    }
  }

  function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'collaboration-notification';
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #22c55e;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 10000;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      animation: fadeIn 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'fadeOut 0.3s ease-out forwards';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  function getCurrentUserId() {
    return localStorage.getItem('user_id') || 'anonymous_' + Math.random().toString(36).substr(2, 9);
  }

  // Auto-save functionality
  let autoSaveTimeout;

  window.scheduleAutoSave = function () {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(async () => {
      if (currentPRDId && editor) {
        try {
          const content = getCurrentEditorContent();
          await savePRDContent(currentPRDId, content);
          console.log('Auto-saved PRD content');
          broadcastContentChange('auto_save', content);
        } catch (error) {
          console.error('Auto-save failed:', error);
        }
      }
    }, 2000);
  };

  // Suggestion card click handler
  window.selectSuggestion = async function (suggestionText) {
    const textEl = document.getElementById('chatInput');
    if (textEl) textEl.value = suggestionText;

    // Automatically send the suggestion
    await window.sendChatMessage();
  };

  // Generate Initial Specs button handler
  window.generateInitialSpecs = async function () {
    const isModifyMode = conversationState.mode === 'modify';
    const actionText = isModifyMode ? 'Apply improvements to PRD' : 'Generate comprehensive PRD';

    appendMsg('user', actionText);

    // Show generation progress in chat with visual progress
    showGenerationProgress(isModifyMode);

    try {
      const response = await fetch('/api/prd-editor/generate-comprehensive-prd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_state: conversationState,
          mode: conversationState.mode,
          current_content: isModifyMode ? await editor.save() : null
        })
      });

      hideGenerationProgress();

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data.editorjs_content) {
          // Load the generated content into the editor
          await editor.render(data.data.editorjs_content);

          // Render any Mermaid diagrams
          setTimeout(renderAllMermaidDiagrams, 500);

          // Update outline
          buildOutline();

          // Show success message
          const successMessage = isModifyMode
            ? '🎉 Perfect! I\'ve applied the improvements to your PRD based on our conversation. The enhanced content is now in the editor.'
            : '🎉 Excellent! I\'ve generated a comprehensive PRD that includes:\n\n• **Product Specification** - Vision, user personas, requirements\n• **Technical Specification** - Architecture, diagrams, data models\n• **Implementation Plan** - Phased development approach';

          appendMsg('ai', successMessage, [], []);

          // Add action buttons for next steps (only for create mode)
          if (!isModifyMode) {
            showNextStepActions();
          }

        } else {
          const fallbackMessage = isModifyMode
            ? 'I had trouble applying the improvements. Let me ask a few more questions to better understand what you want to enhance.'
            : 'I had trouble generating the PRD. Let me ask a few more questions to better understand your project.';
          appendMsg('ai', fallbackMessage, [], []);
        }
      } else {
        const fallbackMessage = isModifyMode
          ? 'I had trouble applying the improvements. Let me ask a few more questions to better understand what you want to enhance.'
          : 'I had trouble generating the PRD. Let me ask a few more questions to better understand your project.';
        appendMsg('ai', fallbackMessage, [], []);
      }

    } catch (error) {
      hideGenerationProgress();
      console.error('Error generating specs:', error);
      const fallbackMessage = isModifyMode
        ? 'I had trouble applying the improvements. Let me ask a few more questions to better understand what you want to enhance.'
        : 'I had trouble generating the PRD. Let me ask a few more questions to better understand your project.';
      appendMsg('ai', fallbackMessage, [], []);
    }
  };

  function showGenerationProgress(isModifyMode = false) {
    const chatBody = document.getElementById('chatBody');
    const progressDiv = document.createElement('div');
    progressDiv.id = 'generation-progress';
    progressDiv.className = 'chat-message ai';

    const headerText = isModifyMode ? 'Applying improvements to PRD' : 'Generating comprehensive documents';
    const steps = isModifyMode ? [
      { icon: '✅', text: 'Analyzing current PRD', width: '100%' },
      { icon: '✅', text: 'Processing improvements', width: '100%' },
      { icon: '⏳', text: 'Applying enhancements', width: '75%' },
      { icon: '⏳', text: 'Finalizing changes', width: '45%' }
    ] : [
      { icon: '✅', text: 'Processing PRD', width: '100%' },
      { icon: '✅', text: 'Creating PRD', width: '100%' },
      { icon: '⏳', text: 'Processing TRD', width: '75%' },
      { icon: '⏳', text: 'Creating TRD', width: '45%' }
    ];

    progressDiv.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px;">AI Assistant</div>
      <div class="generation-status">
        <div class="generation-header">${headerText}</div>
        <div class="generation-steps">
          ${steps.map((step, index) => `
            <div class="generation-step ${index < 2 ? 'active' : ''}">
              <span class="step-icon">${step.icon}</span>
              <span class="step-text">${step.text}</span>
              <div class="step-progress"><div class="progress-bar" style="width: ${step.width}"></div></div>
            </div>
          `).join('')}
        </div>
        <div class="generation-timestamp">${new Date().toLocaleString()}</div>
      </div>
    `;
    chatBody.appendChild(progressDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function hideGenerationProgress() {
    const progress = document.getElementById('generation-progress');
    if (progress) progress.remove();
  }

  function showNextStepActions() {
    const chatBody = document.getElementById('chatBody');
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'chat-message ai';
    actionsDiv.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 8px;">AI Assistant</div>
      <div>Choose what to add next:</div>
      <div class="next-step-actions">
        <button class="action-card" onclick="generateAdditionalSection('ui_ux')">
          <div class="action-icon">🎨</div>
          <div class="action-title">UI/UX Requirements</div>
          <div class="action-description">Add detailed interface and user experience specifications</div>
        </button>
        <button class="action-card" onclick="generateAdditionalSection('implementation')">
          <div class="action-icon">🚀</div>
          <div class="action-title">Implementation Plan</div>
          <div class="action-description">Create detailed development phases and milestones</div>
        </button>
        <button class="action-card" onclick="generateAdditionalSection('api_specs')">
          <div class="action-icon">🔌</div>
          <div class="action-title">API Specifications</div>
          <div class="action-description">Define REST API endpoints and data models</div>
        </button>
        <button class="action-card" onclick="generateAdditionalSection('testing')">
          <div class="action-icon">🧪</div>
          <div class="action-title">Testing Strategy</div>
          <div class="action-description">Add comprehensive testing and QA plans</div>
        </button>
      </div>
    `;
    chatBody.appendChild(actionsDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  // Additional section generation handler
  window.generateAdditionalSection = async function (sectionType) {
    const sectionNames = {
      'ui_ux': 'UI/UX Requirements',
      'implementation': 'Implementation Plan',
      'api_specs': 'API Specifications',
      'testing': 'Testing Strategy'
    };

    appendMsg('user', `Add ${sectionNames[sectionType]}`);
    showTyping();

    try {
      const response = await fetch('/api/prd-editor/generate-additional-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_type: sectionType,
          conversation_state: conversationState,
          current_prd_id: currentPRDId
        })
      });

      hideTyping();

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data.content) {
          // Append the new section to the editor
          const currentContent = await editor.save();
          const newBlocks = data.data.editorjs_blocks || [];

          currentContent.blocks.push(...newBlocks);
          await editor.render(currentContent);

          // Update outline and render diagrams
          buildOutline();
          setTimeout(renderAllMermaidDiagrams, 500);

          appendMsg('ai', `Great! I've added the ${sectionNames[sectionType]} section to your PRD. You can review and edit it in the main editor.`, [], []);
        } else {
          appendMsg('ai', `I had trouble generating the ${sectionNames[sectionType]} section. Please try again.`, [], []);
        }
      } else {
        appendMsg('ai', `I had trouble generating the ${sectionNames[sectionType]} section. Please try again.`, [], []);
      }

    } catch (error) {
      hideTyping();
      console.error('Error generating additional section:', error);
      appendMsg('ai', `I had trouble generating the ${sectionNames[sectionType]} section. Please try again.`, [], []);
    }
  };

  // Suggestion selection handler
  window.selectSuggestion = function (suggestion) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
      chatInput.value = suggestion;
      // Trigger send message
      sendChatMessage();
    }
  };

  // Send chat message function
  async function sendChatMessage() {
    const textEl = document.getElementById('chatInput');
    const message = textEl?.value?.trim();
    if (!message) return;

    // Clear input and add user message
    textEl.value = '';
    appendMsg('user', message);

    // Show typing indicator
    showTyping();

    try {
      // Handle the message based on conversation mode
      const result = await handleAiChatMessage(message);

      hideTyping();

      // Display AI response
      appendMsg('ai', result.message, result.modifications || [], result.suggestions || [], result.show_generate_button || false);

    } catch (error) {
      hideTyping();
      console.error('Chat error:', error);
      appendMsg('ai', 'I encountered an error processing your message. Please try again.');
    }
  }

  // Make all functions globally available
  window.handleAiChatMessage = handleAiChatMessage;
  window.callBackendAI = callBackendAI;
  window.selectPath = selectPath;
  window.sendChatMessage = sendChatMessage;
  window.appendMsg = appendMsg;
  window.createPRDFromFeedItem = createPRDFromFeedItem;
  window.savePRDContent = savePRDContent;
  window.broadcastCollaborationEvent = broadcastCollaborationEvent;
  window.generateComprehensivePRD = generateComprehensivePRD;
  window.generatePRDSection = generatePRDSection;

})();
