/**
 * Notion-like Block Editor System
 * Provides full block-based editing with hover controls
 */

class NotionBlockEditor {
  constructor(container, editorInstance) {
    this.container = container;
    this.editor = editorInstance;
    this.blocks = [];
    this.selectedBlock = null;
    this.init();
  }

  init() {
    // Wait for Editor.js to be ready
    if (this.editor && this.editor.isReady) {
      this.editor.isReady.then(() => {
        this.wrapEditorBlocks();
        this.attachEventListeners();
        this.hideEditorUI();
      });
    } else {
      // Fallback for direct DOM manipulation
      setTimeout(() => this.initDirectMode(), 100);
    }
  }

  initDirectMode() {
    // Create initial structure if editor isn't ready
    this.createNotionStructure();
  }

  hideEditorUI() {
    // Hide Editor.js default UI elements
    const style = document.createElement('style');
    style.textContent = `
      .ce-toolbar { display: none !important; }
      .ce-toolbar__plus { display: none !important; }
      .ce-toolbar__settings-btn { display: none !important; }
      .ce-inline-toolbar { display: none !important; }
    `;
    document.head.appendChild(style);
  }

  wrapEditorBlocks() {
    // Wrap existing Editor.js blocks with Notion-style wrappers
    const blocks = this.container.querySelectorAll('.ce-block');
    blocks.forEach((block, index) => {
      if (!block.classList.contains('notion-wrapped')) {
        this.wrapBlock(block, index);
      }
    });
  }

  wrapBlock(block, index) {
    const wrapper = document.createElement('div');
    wrapper.className = 'notion-block';
    wrapper.setAttribute('data-block-id', `block-${Date.now()}-${index}`);
    
    // Detect block type
    const blockType = this.detectBlockType(block);
    wrapper.setAttribute('data-type', blockType);

    // Create controls
    const controls = this.createBlockControls();
    const dragHandle = this.createDragHandle();
    
    // Wrap the original block content
    const content = document.createElement('div');
    content.className = 'notion-block-content';
    content.contentEditable = true;
    
    // Move block content to wrapper
    while (block.firstChild) {
      content.appendChild(block.firstChild);
    }
    
    wrapper.appendChild(dragHandle);
    wrapper.appendChild(content);
    wrapper.appendChild(controls);
    
    // Replace original block
    block.parentNode.replaceChild(wrapper, block);
    wrapper.classList.add('notion-wrapped');
    
    // Attach block-specific events
    this.attachBlockEvents(wrapper);
    
    // Store reference
    this.blocks.push(wrapper);
  }

  detectBlockType(block) {
    // Detect the type of Editor.js block
    if (block.querySelector('h1')) return 'header-1';
    if (block.querySelector('h2')) return 'header-2';
    if (block.querySelector('h3')) return 'header-3';
    if (block.querySelector('ul')) return 'bullet-list';
    if (block.querySelector('ol')) return 'numbered-list';
    if (block.querySelector('blockquote')) return 'quote';
    if (block.querySelector('code')) return 'code';
    if (block.querySelector('table')) return 'table';
    return 'paragraph';
  }

  createBlockControls() {
    const controls = document.createElement('div');
    controls.className = 'block-controls';
    
    // Add "Create new" text label
    const label = document.createElement('span');
    label.className = 'block-controls-label';
    label.textContent = 'Create new';
    
    // Add above button (green up arrow) - proper white arrow
    const addAbove = document.createElement('button');
    addAbove.className = 'block-control-btn add-above';
    addAbove.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/>
      </svg>
    `;
    addAbove.title = 'Add block above';
    
    // Add below button (green down arrow) - proper white arrow
    const addBelow = document.createElement('button');
    addBelow.className = 'block-control-btn add-below';
    addBelow.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>
      </svg>
    `;
    addBelow.title = 'Add block below';
    
    // Delete button (red trash can) - clean simple trash icon
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'block-control-btn delete';
    deleteBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="3,6 5,6 21,6"></polyline>
        <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
        <line x1="10" y1="11" x2="10" y2="17"></line>
        <line x1="14" y1="11" x2="14" y2="17"></line>
      </svg>
    `;
    deleteBtn.title = 'Delete block';
    
    controls.appendChild(label);
    controls.appendChild(addAbove);
    controls.appendChild(addBelow);
    controls.appendChild(deleteBtn);
    
    return controls;
  }

  createDragHandle() {
    const handle = document.createElement('div');
    handle.className = 'block-drag-handle';
    handle.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M5 3a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zM5 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zM5 13a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
      </svg>
    `;
    handle.draggable = true;
    return handle;
  }

  attachBlockEvents(block) {
    const content = block.querySelector('.notion-block-content');
    const controls = block.querySelector('.block-controls');
    
    // Select block on click
    block.addEventListener('click', (e) => {
      if (!e.target.closest('.block-controls')) {
        this.selectBlock(block);
      }
    });
    
    // Content editing
    content.addEventListener('input', () => {
      this.handleContentChange(block, content);
    });
    
    content.addEventListener('keydown', (e) => {
      this.handleKeyPress(e, block);
    });
    
    // Control buttons
    const addAbove = controls.querySelector('.add-above');
    const addBelow = controls.querySelector('.add-below');
    const deleteBtn = controls.querySelector('.delete');
    
    addAbove.addEventListener('click', (e) => {
      e.stopPropagation();
      this.addBlockAbove(block);
    });
    
    addBelow.addEventListener('click', (e) => {
      e.stopPropagation();
      this.addBlockBelow(block);
    });
    
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.deleteBlock(block);
    });
    
    // Drag and drop
    const dragHandle = block.querySelector('.block-drag-handle');
    this.attachDragEvents(block, dragHandle);
  }

  selectBlock(block) {
    // Deselect previous
    if (this.selectedBlock) {
      this.selectedBlock.classList.remove('selected');
    }
    
    // Select new
    this.selectedBlock = block;
    block.classList.add('selected');
  }

  handleContentChange(block, content) {
    // Update block type based on content
    const text = content.textContent.trim();
    
    if (text.startsWith('# ')) {
      block.setAttribute('data-type', 'header-1');
      content.innerHTML = `<h1>${text.substring(2)}</h1>`;
    } else if (text.startsWith('## ')) {
      block.setAttribute('data-type', 'header-2');
      content.innerHTML = `<h2>${text.substring(3)}</h2>`;
    } else if (text.startsWith('### ')) {
      block.setAttribute('data-type', 'header-3');
      content.innerHTML = `<h3>${text.substring(4)}</h3>`;
    } else if (text.startsWith('- ') || text.startsWith('* ')) {
      block.setAttribute('data-type', 'bullet-list');
    } else if (text.match(/^\d+\. /)) {
      block.setAttribute('data-type', 'numbered-list');
    }
    
    // Sync with Editor.js if available
    this.syncWithEditor();
  }

  handleKeyPress(e, block) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.addBlockBelow(block);
    } else if (e.key === 'Backspace' && block.querySelector('.notion-block-content').textContent === '') {
      e.preventDefault();
      this.deleteBlock(block);
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // Indent block
    }
  }

  addBlockAbove(referenceBlock) {
    const newBlock = this.createNewBlock();
    referenceBlock.parentNode.insertBefore(newBlock, referenceBlock);
    this.focusBlock(newBlock);
    this.syncWithEditor();
  }

  addBlockBelow(referenceBlock) {
    const newBlock = this.createNewBlock();
    referenceBlock.parentNode.insertBefore(newBlock, referenceBlock.nextSibling);
    this.focusBlock(newBlock);
    this.syncWithEditor();
  }

  deleteBlock(block) {
    if (this.blocks.length > 1) {
      const index = this.blocks.indexOf(block);
      const nextBlock = this.blocks[index + 1] || this.blocks[index - 1];
      
      block.remove();
      this.blocks = this.blocks.filter(b => b !== block);
      
      if (nextBlock) {
        this.focusBlock(nextBlock);
      }
      
      this.syncWithEditor();
    }
  }

  createNewBlock(type = 'paragraph', content = '') {
    const wrapper = document.createElement('div');
    wrapper.className = 'notion-block new';
    wrapper.setAttribute('data-block-id', `block-${Date.now()}`);
    wrapper.setAttribute('data-type', type);
    
    const controls = this.createBlockControls();
    const dragHandle = this.createDragHandle();
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'notion-block-content';
    contentDiv.contentEditable = true;
    contentDiv.textContent = content;
    
    wrapper.appendChild(dragHandle);
    wrapper.appendChild(contentDiv);
    wrapper.appendChild(controls);
    
    this.attachBlockEvents(wrapper);
    this.blocks.push(wrapper);
    
    return wrapper;
  }

  focusBlock(block) {
    const content = block.querySelector('.notion-block-content');
    if (content) {
      content.focus();
      // Place cursor at end
      const range = document.createRange();
      const selection = window.getSelection();
      range.selectNodeContents(content);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    this.selectBlock(block);
  }

  attachDragEvents(block, handle) {
    let draggedBlock = null;
    
    handle.addEventListener('dragstart', (e) => {
      draggedBlock = block;
      block.style.opacity = '0.5';
      e.dataTransfer.effectAllowed = 'move';
    });
    
    handle.addEventListener('dragend', () => {
      block.style.opacity = '';
      draggedBlock = null;
    });
    
    block.addEventListener('dragover', (e) => {
      e.preventDefault();
      if (draggedBlock && draggedBlock !== block) {
        const rect = block.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        
        if (e.clientY < midpoint) {
          block.style.borderTop = '2px solid #3b82f6';
          block.style.borderBottom = '';
        } else {
          block.style.borderBottom = '2px solid #3b82f6';
          block.style.borderTop = '';
        }
      }
    });
    
    block.addEventListener('dragleave', () => {
      block.style.borderTop = '';
      block.style.borderBottom = '';
    });
    
    block.addEventListener('drop', (e) => {
      e.preventDefault();
      block.style.borderTop = '';
      block.style.borderBottom = '';
      
      if (draggedBlock && draggedBlock !== block) {
        const rect = block.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        
        if (e.clientY < midpoint) {
          block.parentNode.insertBefore(draggedBlock, block);
        } else {
          block.parentNode.insertBefore(draggedBlock, block.nextSibling);
        }
        
        this.updateBlockOrder();
        this.syncWithEditor();
      }
    });
  }

  updateBlockOrder() {
    this.blocks = Array.from(this.container.querySelectorAll('.notion-block'));
  }

  syncWithEditor() {
    // Sync changes back to Editor.js if available
    if (this.editor && this.editor.save) {
      // Convert Notion blocks to Editor.js format
      const blocksData = this.blocks.map(block => this.blockToEditorData(block));
      // Update editor without re-rendering
      // This would need Editor.js API support
    }
  }

  blockToEditorData(block) {
    const type = block.getAttribute('data-type');
    const content = block.querySelector('.notion-block-content');
    
    const dataMap = {
      'header-1': { type: 'header', data: { text: content.textContent, level: 1 } },
      'header-2': { type: 'header', data: { text: content.textContent, level: 2 } },
      'header-3': { type: 'header', data: { text: content.textContent, level: 3 } },
      'paragraph': { type: 'paragraph', data: { text: content.innerHTML } },
      'bullet-list': { type: 'list', data: { style: 'unordered', items: [content.textContent] } },
      'numbered-list': { type: 'list', data: { style: 'ordered', items: [content.textContent] } },
    };
    
    return dataMap[type] || { type: 'paragraph', data: { text: content.innerHTML } };
  }

  // Create collapsible sections for PRD structure
  createSection(title, type, content) {
    const section = document.createElement('div');
    section.className = 'notion-section';
    section.setAttribute('data-section', type);
    
    const header = document.createElement('div');
    header.className = 'notion-section-header';
    header.innerHTML = `
      <span class="notion-section-arrow">▼</span>
      <span>${title}</span>
    `;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'notion-section-content';
    contentDiv.innerHTML = content;
    
    header.addEventListener('click', () => {
      section.classList.toggle('collapsed');
    });
    
    section.appendChild(header);
    section.appendChild(contentDiv);
    
    return section;
  }

  // Create the PRD structure with collapsible sections
  createNotionStructure() {
    const structure = `
      <div class="notion-prd-structure">
        ${this.createSection('Product Specification', 'product', '<div class="notion-blocks-container"></div>').outerHTML}
        ${this.createSection('Technical Specification', 'technical', '<div class="notion-blocks-container"></div>').outerHTML}
        ${this.createSection('File Trees', 'filetree', '<div class="file-tree"></div>').outerHTML}
        ${this.createSection('Implementation Plan', 'implementation', '<div class="notion-blocks-container"></div>').outerHTML}
      </div>
    `;
    
    this.container.innerHTML = structure;
    
    // Initialize blocks in each section
    const containers = this.container.querySelectorAll('.notion-blocks-container');
    containers.forEach(container => {
      const initialBlock = this.createNewBlock('paragraph', 'Click to start typing...');
      container.appendChild(initialBlock);
    });
  }

  attachEventListeners() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.metaKey || e.ctrlKey) {
        switch(e.key) {
          case 'b': // Bold
            e.preventDefault();
            document.execCommand('bold');
            break;
          case 'i': // Italic
            e.preventDefault();
            document.execCommand('italic');
            break;
          case 'u': // Underline
            e.preventDefault();
            document.execCommand('underline');
            break;
          case 'k': // Link
            e.preventDefault();
            this.insertLink();
            break;
        }
      }
    });

    // Text selection toolbar
    document.addEventListener('mouseup', (e) => {
      const selection = window.getSelection();
      if (selection.toString().length > 0) {
        this.showInlineToolbar(selection);
      } else {
        this.hideInlineToolbar();
      }
    });
  }

  showInlineToolbar(selection) {
    let toolbar = document.querySelector('.inline-toolbar');
    if (!toolbar) {
      toolbar = this.createInlineToolbar();
      document.body.appendChild(toolbar);
    }
    
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    toolbar.style.top = `${rect.top - 40}px`;
    toolbar.style.left = `${rect.left + rect.width / 2 - 70}px`;
    toolbar.classList.add('active');
  }

  hideInlineToolbar() {
    const toolbar = document.querySelector('.inline-toolbar');
    if (toolbar) {
      toolbar.classList.remove('active');
    }
  }

  createInlineToolbar() {
    const toolbar = document.createElement('div');
    toolbar.className = 'inline-toolbar';
    
    const buttons = [
      { command: 'bold', label: 'B' },
      { command: 'italic', label: 'I' },
      { command: 'underline', label: 'U' },
      { command: 'strikethrough', label: 'S' },
      { command: 'createLink', label: '🔗' },
      { command: 'insertUnorderedList', label: '•' },
    ];
    
    buttons.forEach(({ command, label }) => {
      const btn = document.createElement('button');
      btn.className = 'inline-toolbar-btn';
      btn.innerHTML = label;
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (command === 'createLink') {
          this.insertLink();
        } else {
          document.execCommand(command);
        }
      });
      toolbar.appendChild(btn);
    });
    
    return toolbar;
  }

  insertLink() {
    const url = prompt('Enter URL:');
    if (url) {
      document.execCommand('createLink', false, url);
    }
  }
}

// Initialize when DOM is ready
function initNotionBlocks() {
  const editorContainer = document.getElementById('editorjs');
  if (editorContainer && window.editor) {
    window.notionEditor = new NotionBlockEditor(editorContainer, window.editor);
  }
}

// Export for use
window.NotionBlockEditor = NotionBlockEditor;
window.initNotionBlocks = initNotionBlocks;
