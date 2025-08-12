import React, { useState, useEffect } from 'react';
import { DomainPack, DomainKnowledge } from '../../types/adi';
import { adiApi } from '../../services/api/adiApi';

interface KnowledgeManagerProps {
  projectId: string;
  pack: DomainPack | null;
  onUpdate?: (pack: DomainPack) => void;
}

interface KnowledgeUsage {
  knowledgeId: string;
  usageCount: number;
  lastUsed: string;
  contexts: string[];
}

const KnowledgeManager: React.FC<KnowledgeManagerProps> = ({ 
  projectId, 
  pack, 
  onUpdate 
}) => {
  const [knowledge, setKnowledge] = useState<DomainKnowledge[]>([]);
  const [filteredKnowledge, setFilteredKnowledge] = useState<DomainKnowledge[]>([]);
  const [editingKnowledge, setEditingKnowledge] = useState<DomainKnowledge | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [usageAnalytics, setUsageAnalytics] = useState<{ [id: string]: KnowledgeUsage }>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (pack?.pack_data?.knowledge) {
      setKnowledge(pack.pack_data.knowledge);
      setFilteredKnowledge(pack.pack_data.knowledge);
    }
    loadUsageAnalytics();
  }, [pack]);

  useEffect(() => {
    filterKnowledge();
  }, [knowledge, searchQuery, selectedType, selectedTags]);

  const loadUsageAnalytics = async () => {
    try {
      // Mock usage analytics - in real implementation, fetch from backend
      const mockUsage: { [id: string]: KnowledgeUsage } = {};
      
      knowledge.forEach(item => {
        if (item.id) {
          mockUsage[item.id] = {
            knowledgeId: item.id,
            usageCount: Math.floor(Math.random() * 100),
            lastUsed: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
            contexts: ['decision_making', 'validation', 'explanation']
          };
        }
      });
      
      setUsageAnalytics(mockUsage);
    } catch (err) {
      console.error('Failed to load usage analytics:', err);
    }
  };

  const filterKnowledge = () => {
    let filtered = [...knowledge];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item =>
        item.content.toLowerCase().includes(query) ||
        (item.tags && item.tags.some(tag => tag.toLowerCase().includes(query)))
      );
    }

    // Filter by type
    if (selectedType !== 'all') {
      filtered = filtered.filter(item => item.type === selectedType);
    }

    // Filter by tags
    if (selectedTags.length > 0) {
      filtered = filtered.filter(item =>
        item.tags && selectedTags.every(tag => item.tags!.includes(tag))
      );
    }

    setFilteredKnowledge(filtered);
  };

  const getAllTags = (): string[] => {
    const tagSet = new Set<string>();
    knowledge.forEach(item => {
      if (item.tags) {
        item.tags.forEach(tag => tagSet.add(tag));
      }
    });
    return Array.from(tagSet).sort();
  };

  const handleAddKnowledge = () => {
    const newKnowledge: DomainKnowledge = {
      id: `knowledge_${Date.now()}`,
      domain: projectId,
      type: 'context',
      content: '',
      format: 'text',
      tags: [],
      author: 'current_user',
      timestamp: new Date().toISOString()
    };
    setEditingKnowledge(newKnowledge);
    setShowAddForm(true);
  };

  const handleEditKnowledge = (item: DomainKnowledge) => {
    setEditingKnowledge({ ...item });
    setShowAddForm(true);
  };

  const handleSaveKnowledge = async () => {
    if (!editingKnowledge) return;

    const errors = validateKnowledge(editingKnowledge);
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setValidationErrors([]);

      const updatedKnowledge = editingKnowledge.id && knowledge.find(k => k.id === editingKnowledge.id)
        ? knowledge.map(k => k.id === editingKnowledge.id ? editingKnowledge : k)
        : [...knowledge, editingKnowledge];

      await saveKnowledgeToServer(updatedKnowledge);
      
      setKnowledge(updatedKnowledge);
      setShowAddForm(false);
      setEditingKnowledge(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save knowledge');
    } finally {
      setSaving(false);
    }
  };

  const validateKnowledge = (item: DomainKnowledge): string[] => {
    const errors: string[] = [];
    
    if (!item.content.trim()) errors.push('Content is required');
    if (!item.type) errors.push('Type is required');
    if (!item.format) errors.push('Format is required');
    
    return errors;
  };

  const saveKnowledgeToServer = async (updatedKnowledge: DomainKnowledge[]) => {
    const updatedPack = await adiApi.updateDomainPack(projectId, {
      pack_data: {
        ...pack?.pack_data,
        knowledge: updatedKnowledge
      }
    });

    onUpdate?.(updatedPack);
  };

  const handleDeleteKnowledge = async (knowledgeId: string) => {
    if (!confirm('Are you sure you want to delete this knowledge item?')) return;

    try {
      setSaving(true);
      setError(null);

      const updatedKnowledge = knowledge.filter(k => k.id !== knowledgeId);
      await saveKnowledgeToServer(updatedKnowledge);
      
      setKnowledge(updatedKnowledge);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete knowledge');
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicateKnowledge = (item: DomainKnowledge) => {
    const duplicated: DomainKnowledge = {
      ...item,
      id: `knowledge_${Date.now()}`,
      content: `${item.content} (Copy)`,
      timestamp: new Date().toISOString()
    };
    setEditingKnowledge(duplicated);
    setShowAddForm(true);
  };

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const getKnowledgeTypeIcon = (type: DomainKnowledge['type']): string => {
    switch (type) {
      case 'policy': return '📋';
      case 'rule': return '⚖️';
      case 'example': return '💡';
      case 'context': return '📝';
      default: return '📄';
    }
  };

  const getFormatIcon = (format: DomainKnowledge['format']): string => {
    switch (format) {
      case 'yaml': return '🔧';
      case 'json': return '{}';
      case 'text': return '📝';
      default: return '📄';
    }
  };

  const allTags = getAllTags();

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Header and Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Knowledge Base</h3>
            <p className="text-sm text-gray-600">
              Manage domain knowledge, policies, and examples
            </p>
          </div>
          <button
            onClick={handleAddKnowledge}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Add Knowledge
          </button>
        </div>

        {/* Search and Filters */}
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search knowledge content and tags..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              <option value="policy">Policy</option>
              <option value="rule">Rule</option>
              <option value="example">Example</option>
              <option value="context">Context</option>
            </select>
          </div>

          {/* Tag Filters */}
          {allTags.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Tags:
              </label>
              <div className="flex flex-wrap gap-2">
                {allTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleTagToggle(tag)}
                    className={`px-3 py-1 text-sm rounded-full border ${
                      selectedTags.includes(tag)
                        ? 'bg-blue-100 text-blue-800 border-blue-300'
                        : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 text-sm text-gray-600">
          <p><strong>Total Items:</strong> {knowledge.length}</p>
          <p><strong>Filtered:</strong> {filteredKnowledge.length}</p>
        </div>
      </div>

      {/* Knowledge Items */}
      <div className="space-y-4">
        {filteredKnowledge.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500 mb-4">
              {knowledge.length === 0 
                ? 'No knowledge items yet.' 
                : 'No items match your current filters.'
              }
            </p>
            {knowledge.length === 0 && (
              <button
                onClick={handleAddKnowledge}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Add Your First Knowledge Item
              </button>
            )}
          </div>
        ) : (
          filteredKnowledge.map((item) => (
            <KnowledgeCard
              key={item.id}
              knowledge={item}
              usage={item.id ? usageAnalytics[item.id] : undefined}
              onEdit={() => handleEditKnowledge(item)}
              onDelete={() => handleDeleteKnowledge(item.id!)}
              onDuplicate={() => handleDuplicateKnowledge(item)}
              saving={saving}
              getTypeIcon={getKnowledgeTypeIcon}
              getFormatIcon={getFormatIcon}
            />
          ))
        )}
      </div>

      {/* Add/Edit Knowledge Modal */}
      {showAddForm && editingKnowledge && (
        <KnowledgeEditModal
          knowledge={editingKnowledge}
          onSave={handleSaveKnowledge}
          onCancel={() => {
            setShowAddForm(false);
            setEditingKnowledge(null);
            setValidationErrors([]);
          }}
          onChange={setEditingKnowledge}
          saving={saving}
          validationErrors={validationErrors}
          availableTags={allTags}
        />
      )}
    </div>
  );
};

// Knowledge Card Component
interface KnowledgeCardProps {
  knowledge: DomainKnowledge;
  usage?: KnowledgeUsage;
  onEdit: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
  saving: boolean;
  getTypeIcon: (type: DomainKnowledge['type']) => string;
  getFormatIcon: (format: DomainKnowledge['format']) => string;
}

const KnowledgeCard: React.FC<KnowledgeCardProps> = ({ 
  knowledge, 
  usage, 
  onEdit, 
  onDelete, 
  onDuplicate, 
  saving,
  getTypeIcon,
  getFormatIcon
}) => (
  <div className="bg-white rounded-lg shadow border-l-4 border-green-500 p-6">
    <div className="flex items-start justify-between mb-4">
      <div className="flex-1">
        <div className="flex items-center space-x-2 mb-2">
          <span className="text-lg">{getTypeIcon(knowledge.type)}</span>
          <span className="text-sm">{getFormatIcon(knowledge.format)}</span>
          <span className={`px-2 py-1 text-xs rounded ${
            knowledge.type === 'policy' ? 'bg-blue-100 text-blue-800' :
            knowledge.type === 'rule' ? 'bg-purple-100 text-purple-800' :
            knowledge.type === 'example' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {knowledge.type}
          </span>
          <span className="text-xs text-gray-500">
            {knowledge.format.toUpperCase()}
          </span>
        </div>

        <div className="mb-3">
          <div className="text-sm text-gray-900 whitespace-pre-wrap line-clamp-4">
            {knowledge.content}
          </div>
        </div>

        {/* Tags */}
        {knowledge.tags && knowledge.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {knowledge.tags.map(tag => (
              <span
                key={tag}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Metadata */}
        <div className="flex items-center space-x-4 text-xs text-gray-500">
          {knowledge.author && (
            <span>By: {knowledge.author}</span>
          )}
          {knowledge.timestamp && (
            <span>
              {new Date(knowledge.timestamp).toLocaleDateString()}
            </span>
          )}
          {usage && (
            <>
              <span>Used: {usage.usageCount} times</span>
              <span>
                Last: {new Date(usage.lastUsed).toLocaleDateString()}
              </span>
            </>
          )}
        </div>

        {/* YAML Rule Preview */}
        {knowledge.format === 'yaml' && (
          <div className="mt-3 p-2 bg-gray-50 rounded text-xs font-mono">
            <div className="text-gray-600 mb-1">YAML Content:</div>
            <div className="whitespace-pre-wrap line-clamp-3">
              {knowledge.content}
            </div>
          </div>
        )}
      </div>
      
      <div className="flex items-center space-x-1 ml-4">
        <button
          onClick={onDuplicate}
          disabled={saving}
          className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
          title="Duplicate"
        >
          📋
        </button>
        <button
          onClick={onEdit}
          disabled={saving}
          className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
          title="Edit"
        >
          ✏️
        </button>
        <button
          onClick={onDelete}
          disabled={saving}
          className="p-2 text-red-400 hover:text-red-600 disabled:opacity-50"
          title="Delete"
        >
          🗑️
        </button>
      </div>
    </div>

    {/* Usage Analytics */}
    {usage && (
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Usage Count:</span>
            <span className="ml-2 font-medium">{usage.usageCount}</span>
          </div>
          <div>
            <span className="text-gray-600">Contexts:</span>
            <span className="ml-2 font-medium">{usage.contexts.length}</span>
          </div>
          <div>
            <span className="text-gray-600">Last Used:</span>
            <span className="ml-2 font-medium">
              {new Date(usage.lastUsed).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    )}
  </div>
);

// Knowledge Edit Modal Component
interface KnowledgeEditModalProps {
  knowledge: DomainKnowledge;
  onSave: () => void;
  onCancel: () => void;
  onChange: (knowledge: DomainKnowledge) => void;
  saving: boolean;
  validationErrors: string[];
  availableTags: string[];
}

const KnowledgeEditModal: React.FC<KnowledgeEditModalProps> = ({ 
  knowledge, 
  onSave, 
  onCancel, 
  onChange, 
  saving, 
  validationErrors,
  availableTags
}) => {
  const [newTag, setNewTag] = useState('');

  const addTag = () => {
    if (newTag.trim() && !knowledge.tags?.includes(newTag.trim())) {
      onChange({
        ...knowledge,
        tags: [...(knowledge.tags || []), newTag.trim()]
      });
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    onChange({
      ...knowledge,
      tags: knowledge.tags?.filter(tag => tag !== tagToRemove) || []
    });
  };

  const addExistingTag = (tag: string) => {
    if (!knowledge.tags?.includes(tag)) {
      onChange({
        ...knowledge,
        tags: [...(knowledge.tags || []), tag]
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-medium mb-4">
          {knowledge.id?.startsWith('knowledge_new') ? 'Add Knowledge' : 'Edit Knowledge'}
        </h3>

        {validationErrors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <ul className="list-disc list-inside text-red-700 text-sm">
              {validationErrors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-4">
          {/* Type and Format */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Type *
              </label>
              <select
                value={knowledge.type}
                onChange={(e) => onChange({ ...knowledge, type: e.target.value as DomainKnowledge['type'] })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="policy">Policy</option>
                <option value="rule">Rule</option>
                <option value="example">Example</option>
                <option value="context">Context</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Format *
              </label>
              <select
                value={knowledge.format}
                onChange={(e) => onChange({ ...knowledge, format: e.target.value as DomainKnowledge['format'] })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="text">Text</option>
                <option value="yaml">YAML</option>
                <option value="json">JSON</option>
              </select>
            </div>
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Content *
            </label>
            <textarea
              value={knowledge.content}
              onChange={(e) => onChange({ ...knowledge, content: e.target.value })}
              rows={knowledge.format === 'yaml' || knowledge.format === 'json' ? 12 : 8}
              className={`w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                knowledge.format === 'yaml' || knowledge.format === 'json' ? 'font-mono text-sm' : ''
              }`}
              placeholder={
                knowledge.format === 'yaml' 
                  ? 'Enter YAML content...\n\nExample:\nrule:\n  condition: "confidence > 0.8"\n  action: "approve"'
                  : knowledge.format === 'json'
                  ? 'Enter JSON content...\n\n{\n  "rule": {\n    "condition": "confidence > 0.8",\n    "action": "approve"\n  }\n}'
                  : 'Enter knowledge content, policies, examples, or context information...'
              }
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags
            </label>
            
            {/* Current Tags */}
            {knowledge.tags && knowledge.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {knowledge.tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-3 py-1 text-sm bg-blue-100 text-blue-800 rounded-full"
                  >
                    #{tag}
                    <button
                      onClick={() => removeTag(tag)}
                      className="ml-2 text-blue-600 hover:text-blue-800"
                    >
                      ✕
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Add New Tag */}
            <div className="flex items-center space-x-2 mb-3">
              <input
                type="text"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addTag()}
                placeholder="Add new tag..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addTag}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Add
              </button>
            </div>

            {/* Existing Tags */}
            {availableTags.length > 0 && (
              <div>
                <p className="text-sm text-gray-600 mb-2">Or select from existing tags:</p>
                <div className="flex flex-wrap gap-2">
                  {availableTags
                    .filter(tag => !knowledge.tags?.includes(tag))
                    .map(tag => (
                      <button
                        key={tag}
                        onClick={() => addExistingTag(tag)}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      >
                        #{tag}
                      </button>
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* Source Link */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Source Link (Optional)
            </label>
            <input
              type="url"
              value={knowledge.source_link || ''}
              onChange={(e) => onChange({ ...knowledge, source_link: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://..."
            />
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 mt-6">
          <button
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Knowledge'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeManager;