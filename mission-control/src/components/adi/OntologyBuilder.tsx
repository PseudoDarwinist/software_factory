import React, { useState, useEffect, useRef } from 'react';
import { DomainPack, FailureMode } from '../../types/adi';
import { adiApi } from '../../services/api/adiApi';

interface OntologyBuilderProps {
  projectId: string;
  pack: DomainPack | null;
  onUpdate?: (pack: DomainPack) => void;
}

interface OntologyGroup {
  id: string;
  name: string;
  color: string;
  failureModes: FailureMode[];
}

const OntologyBuilder: React.FC<OntologyBuilderProps> = ({ 
  projectId, 
  pack, 
  onUpdate 
}) => {
  const [groups, setGroups] = useState<OntologyGroup[]>([]);
  const [editingMode, setEditingMode] = useState<FailureMode | null>(null);
  const [editingGroup, setEditingGroup] = useState<OntologyGroup | null>(null);
  const [showAddModeForm, setShowAddModeForm] = useState(false);
  const [showAddGroupForm, setShowAddGroupForm] = useState(false);
  const [draggedItem, setDraggedItem] = useState<{ type: 'mode' | 'group'; item: any } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const dragOverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pack?.pack_data?.ontology) {
      organizeOntologyIntoGroups(pack.pack_data.ontology);
    }
  }, [pack]);

  const organizeOntologyIntoGroups = (ontology: FailureMode[]) => {
    const groupMap = new Map<string, OntologyGroup>();
    
    ontology.forEach(mode => {
      const groupName = mode.category || 'Uncategorized';
      
      if (!groupMap.has(groupName)) {
        groupMap.set(groupName, {
          id: `group_${groupName.toLowerCase().replace(/\s+/g, '_')}`,
          name: groupName,
          color: getGroupColor(groupName),
          failureModes: []
        });
      }
      
      groupMap.get(groupName)!.failureModes.push(mode);
    });

    setGroups(Array.from(groupMap.values()));
  };

  const getGroupColor = (groupName: string): string => {
    const colors = [
      '#EF4444', '#F97316', '#F59E0B', '#EAB308',
      '#84CC16', '#22C55E', '#10B981', '#14B8A6',
      '#06B6D4', '#0EA5E9', '#3B82F6', '#6366F1',
      '#8B5CF6', '#A855F7', '#D946EF', '#EC4899'
    ];
    
    let hash = 0;
    for (let i = 0; i < groupName.length; i++) {
      hash = groupName.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    return colors[Math.abs(hash) % colors.length];
  };

  const handleAddGroup = () => {
    const newGroup: OntologyGroup = {
      id: `group_${Date.now()}`,
      name: '',
      color: getGroupColor('new'),
      failureModes: []
    };
    setEditingGroup(newGroup);
    setShowAddGroupForm(true);
  };

  const handleSaveGroup = async () => {
    if (!editingGroup) return;

    if (!editingGroup.name.trim()) {
      setError('Group name is required');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const updatedGroups = editingGroup.id.startsWith('group_new') || !groups.find(g => g.id === editingGroup.id)
        ? [...groups, editingGroup]
        : groups.map(g => g.id === editingGroup.id ? editingGroup : g);

      setGroups(updatedGroups);
      await saveOntologyToServer(updatedGroups);
      
      setShowAddGroupForm(false);
      setEditingGroup(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save group');
    } finally {
      setSaving(false);
    }
  };

  const handleAddFailureMode = (groupId: string) => {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;

    const newMode: FailureMode = {
      id: `mode_${Date.now()}`,
      name: '',
      category: group.name,
      description: '',
      severity: 'medium'
    };
    
    setEditingMode(newMode);
    setShowAddModeForm(true);
  };

  const handleSaveFailureMode = async () => {
    if (!editingMode) return;

    const errors = validateFailureMode(editingMode);
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setValidationErrors([]);

      const updatedGroups = groups.map(group => {
        if (group.name === editingMode.category) {
          const existingIndex = group.failureModes.findIndex(m => m.id === editingMode.id);
          if (existingIndex >= 0) {
            // Update existing
            return {
              ...group,
              failureModes: group.failureModes.map(m => m.id === editingMode.id ? editingMode : m)
            };
          } else {
            // Add new
            return {
              ...group,
              failureModes: [...group.failureModes, editingMode]
            };
          }
        }
        return group;
      });

      setGroups(updatedGroups);
      await saveOntologyToServer(updatedGroups);
      
      setShowAddModeForm(false);
      setEditingMode(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save failure mode');
    } finally {
      setSaving(false);
    }
  };

  const validateFailureMode = (mode: FailureMode): string[] => {
    const errors: string[] = [];
    
    if (!mode.name.trim()) errors.push('Name is required');
    if (!mode.description.trim()) errors.push('Description is required');
    if (!mode.category.trim()) errors.push('Category is required');
    
    // Check for duplicate names within the same category
    const group = groups.find(g => g.name === mode.category);
    if (group && group.failureModes.some(m => m.name === mode.name && m.id !== mode.id)) {
      errors.push('Name must be unique within the category');
    }

    return errors;
  };

  const saveOntologyToServer = async (updatedGroups: OntologyGroup[]) => {
    const flatOntology = updatedGroups.flatMap(group => group.failureModes);
    
    const updatedPack = await adiApi.updateDomainPack(projectId, {
      pack_data: {
        ...pack?.pack_data,
        ontology: flatOntology
      }
    });

    onUpdate?.(updatedPack);
  };

  const handleDeleteFailureMode = async (groupId: string, modeId: string) => {
    if (!confirm('Are you sure you want to delete this failure mode?')) return;

    try {
      setSaving(true);
      setError(null);

      const updatedGroups = groups.map(group => {
        if (group.id === groupId) {
          return {
            ...group,
            failureModes: group.failureModes.filter(m => m.id !== modeId)
          };
        }
        return group;
      });

      setGroups(updatedGroups);
      await saveOntologyToServer(updatedGroups);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete failure mode');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;

    if (group.failureModes.length > 0) {
      if (!confirm(`This group contains ${group.failureModes.length} failure modes. Are you sure you want to delete it?`)) {
        return;
      }
    }

    try {
      setSaving(true);
      setError(null);

      const updatedGroups = groups.filter(g => g.id !== groupId);
      setGroups(updatedGroups);
      await saveOntologyToServer(updatedGroups);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete group');
    } finally {
      setSaving(false);
    }
  };

  // Drag and Drop handlers
  const handleDragStart = (e: React.DragEvent, type: 'mode' | 'group', item: any) => {
    setDraggedItem({ type, item });
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetGroupId: string) => {
    e.preventDefault();
    
    if (!draggedItem || draggedItem.type !== 'mode') return;

    const sourceMode = draggedItem.item as FailureMode;
    const targetGroup = groups.find(g => g.id === targetGroupId);
    
    if (!targetGroup || sourceMode.category === targetGroup.name) return;

    try {
      setSaving(true);
      setError(null);

      const updatedGroups = groups.map(group => {
        if (group.name === sourceMode.category) {
          // Remove from source group
          return {
            ...group,
            failureModes: group.failureModes.filter(m => m.id !== sourceMode.id)
          };
        } else if (group.id === targetGroupId) {
          // Add to target group
          const updatedMode = { ...sourceMode, category: group.name };
          return {
            ...group,
            failureModes: [...group.failureModes, updatedMode]
          };
        }
        return group;
      });

      setGroups(updatedGroups);
      await saveOntologyToServer(updatedGroups);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move failure mode');
    } finally {
      setSaving(false);
      setDraggedItem(null);
    }
  };

  const validateOntology = (): string[] => {
    const errors: string[] = [];
    const allModes = groups.flatMap(g => g.failureModes);
    const names = new Set<string>();
    
    allModes.forEach(mode => {
      if (names.has(mode.name)) {
        errors.push(`Duplicate failure mode name: ${mode.name}`);
      } else {
        names.add(mode.name);
      }
    });

    return errors;
  };

  const ontologyErrors = validateOntology();

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {ontologyErrors.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-medium text-yellow-800 mb-2">Validation Issues:</h4>
          <ul className="list-disc list-inside text-yellow-700 text-sm">
            {ontologyErrors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Failure Mode Ontology</h3>
            <p className="text-sm text-gray-600">
              Organize failure modes into categories with drag-and-drop
            </p>
          </div>
          <button
            onClick={handleAddGroup}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Add Category
          </button>
        </div>

        <div className="text-sm text-gray-600">
          <p><strong>Total Categories:</strong> {groups.length}</p>
          <p><strong>Total Failure Modes:</strong> {groups.reduce((sum, g) => sum + g.failureModes.length, 0)}</p>
        </div>
      </div>

      {/* Ontology Groups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {groups.map((group) => (
          <div
            key={group.id}
            className="bg-white rounded-lg shadow border-l-4"
            style={{ borderLeftColor: group.color }}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, group.id)}
          >
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: group.color }}
                  />
                  <h4 className="font-medium text-gray-900">{group.name}</h4>
                  <span className="text-sm text-gray-500">
                    ({group.failureModes.length})
                  </span>
                </div>
                
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleAddFailureMode(group.id)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Add failure mode"
                  >
                    ➕
                  </button>
                  <button
                    onClick={() => {
                      setEditingGroup({ ...group });
                      setShowAddGroupForm(true);
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Edit group"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDeleteGroup(group.id)}
                    disabled={saving}
                    className="p-1 text-red-400 hover:text-red-600 disabled:opacity-50"
                    title="Delete group"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>

            <div className="p-4 space-y-2 min-h-[100px]">
              {group.failureModes.length === 0 ? (
                <p className="text-gray-500 text-sm italic text-center py-4">
                  No failure modes yet. Drag modes here or click + to add.
                </p>
              ) : (
                group.failureModes.map((mode) => (
                  <div
                    key={mode.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'mode', mode)}
                    className="p-3 bg-gray-50 rounded border cursor-move hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h5 className="font-medium text-sm">{mode.name}</h5>
                          <span className={`px-2 py-1 text-xs rounded ${
                            mode.severity === 'critical' ? 'bg-red-100 text-red-800' :
                            mode.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                            mode.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {mode.severity}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                          {mode.description}
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-1 ml-2">
                        <button
                          onClick={() => {
                            setEditingMode({ ...mode });
                            setShowAddModeForm(true);
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600"
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeleteFailureMode(group.id, mode.id)}
                          disabled={saving}
                          className="p-1 text-red-400 hover:text-red-600 disabled:opacity-50"
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add/Edit Group Modal */}
      {showAddGroupForm && editingGroup && (
        <GroupEditModal
          group={editingGroup}
          onSave={handleSaveGroup}
          onCancel={() => {
            setShowAddGroupForm(false);
            setEditingGroup(null);
            setError(null);
          }}
          onChange={setEditingGroup}
          saving={saving}
        />
      )}

      {/* Add/Edit Failure Mode Modal */}
      {showAddModeForm && editingMode && (
        <FailureModeEditModal
          mode={editingMode}
          groups={groups}
          onSave={handleSaveFailureMode}
          onCancel={() => {
            setShowAddModeForm(false);
            setEditingMode(null);
            setError(null);
            setValidationErrors([]);
          }}
          onChange={setEditingMode}
          saving={saving}
          validationErrors={validationErrors}
        />
      )}
    </div>
  );
};

// Group Edit Modal Component
interface GroupEditModalProps {
  group: OntologyGroup;
  onSave: () => void;
  onCancel: () => void;
  onChange: (group: OntologyGroup) => void;
  saving: boolean;
}

const GroupEditModal: React.FC<GroupEditModalProps> = ({ 
  group, 
  onSave, 
  onCancel, 
  onChange, 
  saving 
}) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div className="bg-white rounded-lg p-6 w-full max-w-md">
      <h3 className="text-lg font-medium mb-4">
        {group.name ? 'Edit Category' : 'Add New Category'}
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Category Name *
          </label>
          <input
            type="text"
            value={group.name}
            onChange={(e) => onChange({ ...group, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Data Quality Issues"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Color
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={group.color}
              onChange={(e) => onChange({ ...group, color: e.target.value })}
              className="w-12 h-8 border border-gray-300 rounded"
            />
            <span className="text-sm text-gray-600">{group.color}</span>
          </div>
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
          {saving ? 'Saving...' : 'Save Category'}
        </button>
      </div>
    </div>
  </div>
);

// Failure Mode Edit Modal Component
interface FailureModeEditModalProps {
  mode: FailureMode;
  groups: OntologyGroup[];
  onSave: () => void;
  onCancel: () => void;
  onChange: (mode: FailureMode) => void;
  saving: boolean;
  validationErrors: string[];
}

const FailureModeEditModal: React.FC<FailureModeEditModalProps> = ({ 
  mode, 
  groups, 
  onSave, 
  onCancel, 
  onChange, 
  saving, 
  validationErrors 
}) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <h3 className="text-lg font-medium mb-4">
        {mode.name ? 'Edit Failure Mode' : 'Add New Failure Mode'}
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
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name *
            </label>
            <input
              type="text"
              value={mode.name}
              onChange={(e) => onChange({ ...mode, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Missing Required Field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category *
            </label>
            <select
              value={mode.category}
              onChange={(e) => onChange({ ...mode, category: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select category...</option>
              {groups.map((group) => (
                <option key={group.id} value={group.name}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Severity *
          </label>
          <select
            value={mode.severity}
            onChange={(e) => onChange({ ...mode, severity: e.target.value as FailureMode['severity'] })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            value={mode.description}
            onChange={(e) => onChange({ ...mode, description: e.target.value })}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Describe when this failure mode occurs and its impact..."
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
          {saving ? 'Saving...' : 'Save Failure Mode'}
        </button>
      </div>
    </div>
  </div>
);

export default OntologyBuilder;