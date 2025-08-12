import React, { useState, useEffect, useRef } from 'react';
import { DomainPack, PolicyRule } from '../../types/adi';
import { adiApi } from '../../services/api/adiApi';

interface RulesEditorProps {
  projectId: string;
  pack: DomainPack | null;
  onUpdate?: (pack: DomainPack) => void;
}

interface RuleVersion {
  version: string;
  timestamp: string;
  author: string;
  changes: string;
  rules: PolicyRule[];
}

const RulesEditor: React.FC<RulesEditorProps> = ({ 
  projectId, 
  pack, 
  onUpdate 
}) => {
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [yamlContent, setYamlContent] = useState('');
  const [editMode, setEditMode] = useState<'visual' | 'yaml'>('visual');
  const [editingRule, setEditingRule] = useState<PolicyRule | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [testCases, setTestCases] = useState<any[]>([]);
  const [testResults, setTestResults] = useState<{ [ruleId: string]: any }>({});
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>('current');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [conflicts, setConflicts] = useState<string[]>([]);

  const yamlEditorRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (pack?.pack_data?.rules) {
      setRules(pack.pack_data.rules);
      setYamlContent(convertRulesToYaml(pack.pack_data.rules));
    }
    loadVersionHistory();
  }, [pack]);

  const convertRulesToYaml = (rules: PolicyRule[]): string => {
    if (rules.length === 0) {
      return `# Domain Rules Configuration
# Define rules that govern decision-making in this domain

rules: []

# Example rule structure:
# rules:
#   - id: "example_rule"
#     description: "Example rule description"
#     applies_when:
#       domain: "example"
#       confidence: ">= 0.8"
#     expect:
#       action: "approve"
#       reasoning_required: true
`;
    }

    let yaml = `# Domain Rules Configuration
# Define rules that govern decision-making in this domain

rules:
`;

    rules.forEach(rule => {
      yaml += `  - id: "${rule.id}"
    description: "${rule.description}"
    applies_when:
`;
      
      Object.entries(rule.applies_when).forEach(([key, value]) => {
        yaml += `      ${key}: ${typeof value === 'string' ? `"${value}"` : value}
`;
      });

      yaml += `    expect:
`;
      
      Object.entries(rule.expect).forEach(([key, value]) => {
        yaml += `      ${key}: ${typeof value === 'string' ? `"${value}"` : value}
`;
      });

      yaml += `
`;
    });

    return yaml;
  };

  const parseYamlToRules = (yaml: string): PolicyRule[] => {
    try {
      // Simple YAML parsing for rules structure
      // In a real implementation, you'd use a proper YAML parser
      const lines = yaml.split('\n');
      const rules: PolicyRule[] = [];
      let currentRule: Partial<PolicyRule> | null = null;
      let currentSection: 'applies_when' | 'expect' | null = null;

      for (const line of lines) {
        const trimmed = line.trim();
        
        if (trimmed.startsWith('- id:')) {
          if (currentRule) {
            rules.push(currentRule as PolicyRule);
          }
          currentRule = {
            id: trimmed.match(/"([^"]+)"/)?.[1] || '',
            description: '',
            applies_when: {},
            expect: {}
          };
          currentSection = null;
        } else if (currentRule && trimmed.startsWith('description:')) {
          currentRule.description = trimmed.match(/"([^"]+)"/)?.[1] || '';
        } else if (trimmed === 'applies_when:') {
          currentSection = 'applies_when';
        } else if (trimmed === 'expect:') {
          currentSection = 'expect';
        } else if (currentRule && currentSection && trimmed.includes(':')) {
          const [key, value] = trimmed.split(':').map(s => s.trim());
          const cleanValue = value.replace(/"/g, '');
          
          if (currentSection === 'applies_when') {
            currentRule.applies_when![key] = cleanValue;
          } else if (currentSection === 'expect') {
            currentRule.expect![key] = cleanValue;
          }
        }
      }

      if (currentRule) {
        rules.push(currentRule as PolicyRule);
      }

      return rules;
    } catch (err) {
      throw new Error('Invalid YAML format');
    }
  };

  const loadVersionHistory = async () => {
    try {
      // Mock version history - in real implementation, fetch from backend
      const mockVersions: RuleVersion[] = [
        {
          version: 'current',
          timestamp: new Date().toISOString(),
          author: 'current user',
          changes: 'Current working version',
          rules: rules
        }
      ];
      setVersions(mockVersions);
    } catch (err) {
      console.error('Failed to load version history:', err);
    }
  };

  const handleAddRule = () => {
    const newRule: PolicyRule = {
      id: '',
      description: '',
      applies_when: {},
      expect: {}
    };
    setEditingRule(newRule);
    setShowAddForm(true);
  };

  const handleEditRule = (rule: PolicyRule) => {
    setEditingRule({ ...rule });
    setShowAddForm(true);
  };

  const handleSaveRule = async () => {
    if (!editingRule) return;

    const errors = validateRule(editingRule);
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setValidationErrors([]);

      const updatedRules = editingRule.id && rules.find(r => r.id === editingRule.id)
        ? rules.map(r => r.id === editingRule.id ? editingRule : r)
        : [...rules, editingRule];

      // Check for conflicts
      const ruleConflicts = detectRuleConflicts(updatedRules);
      if (ruleConflicts.length > 0) {
        setConflicts(ruleConflicts);
        // Allow saving but show warnings
      }

      await saveRulesToServer(updatedRules);
      
      setRules(updatedRules);
      setYamlContent(convertRulesToYaml(updatedRules));
      setShowAddForm(false);
      setEditingRule(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rule');
    } finally {
      setSaving(false);
    }
  };

  const validateRule = (rule: PolicyRule): string[] => {
    const errors: string[] = [];
    
    if (!rule.id.trim()) errors.push('Rule ID is required');
    if (!rule.description.trim()) errors.push('Description is required');
    if (Object.keys(rule.applies_when).length === 0) errors.push('At least one condition is required');
    if (Object.keys(rule.expect).length === 0) errors.push('At least one expectation is required');
    
    // Check for duplicate IDs
    if (rules.some(r => r.id === rule.id && r !== editingRule)) {
      errors.push('Rule ID must be unique');
    }

    return errors;
  };

  const detectRuleConflicts = (rules: PolicyRule[]): string[] => {
    const conflicts: string[] = [];
    
    // Simple conflict detection - check for overlapping conditions with different expectations
    for (let i = 0; i < rules.length; i++) {
      for (let j = i + 1; j < rules.length; j++) {
        const rule1 = rules[i];
        const rule2 = rules[j];
        
        // Check if conditions overlap
        const overlappingKeys = Object.keys(rule1.applies_when).filter(key => 
          key in rule2.applies_when
        );
        
        if (overlappingKeys.length > 0) {
          const hasConflictingExpectations = Object.keys(rule1.expect).some(key => 
            key in rule2.expect && rule1.expect[key] !== rule2.expect[key]
          );
          
          if (hasConflictingExpectations) {
            conflicts.push(`Rules "${rule1.id}" and "${rule2.id}" have conflicting expectations for overlapping conditions`);
          }
        }
      }
    }
    
    return conflicts;
  };

  const saveRulesToServer = async (updatedRules: PolicyRule[]) => {
    const updatedPack = await adiApi.updateDomainPack(projectId, {
      pack_data: {
        ...pack?.pack_data,
        rules: updatedRules
      }
    });

    onUpdate?.(updatedPack);
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
      setSaving(true);
      setError(null);

      const updatedRules = rules.filter(r => r.id !== ruleId);
      await saveRulesToServer(updatedRules);
      
      setRules(updatedRules);
      setYamlContent(convertRulesToYaml(updatedRules));

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule');
    } finally {
      setSaving(false);
    }
  };

  const handleYamlSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setValidationErrors([]);

      const parsedRules = parseYamlToRules(yamlContent);
      
      // Validate all rules
      const allErrors: string[] = [];
      parsedRules.forEach((rule, index) => {
        const errors = validateRule(rule);
        errors.forEach(error => allErrors.push(`Rule ${index + 1}: ${error}`));
      });

      if (allErrors.length > 0) {
        setValidationErrors(allErrors);
        return;
      }

      // Check for conflicts
      const ruleConflicts = detectRuleConflicts(parsedRules);
      if (ruleConflicts.length > 0) {
        setConflicts(ruleConflicts);
      }

      await saveRulesToServer(parsedRules);
      setRules(parsedRules);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse or save YAML');
    } finally {
      setSaving(false);
    }
  };

  const handleTestRules = async () => {
    try {
      setTesting(true);
      setError(null);

      // Mock test cases - in real implementation, these would come from actual data
      const mockTestCases = [
        {
          id: 'test_1',
          domain: 'example',
          confidence: 0.9,
          request_type: 'approval'
        },
        {
          id: 'test_2',
          domain: 'example',
          confidence: 0.5,
          request_type: 'review'
        }
      ];

      setTestCases(mockTestCases);

      // Test each rule against test cases
      const results: { [ruleId: string]: any } = {};
      
      rules.forEach(rule => {
        const ruleResults = mockTestCases.map(testCase => {
          // Simple rule matching logic
          const matches = Object.entries(rule.applies_when).every(([key, condition]) => {
            const testValue = testCase[key as keyof typeof testCase];
            
            if (typeof condition === 'string' && condition.includes('>=')) {
              const threshold = parseFloat(condition.replace('>= ', ''));
              return typeof testValue === 'number' && testValue >= threshold;
            } else if (typeof condition === 'string' && condition.includes('<=')) {
              const threshold = parseFloat(condition.replace('<= ', ''));
              return typeof testValue === 'number' && testValue <= threshold;
            } else {
              return testValue === condition;
            }
          });

          return {
            testCaseId: testCase.id,
            matches,
            expectedAction: matches ? rule.expect : null
          };
        });

        results[rule.id] = {
          totalTests: mockTestCases.length,
          matches: ruleResults.filter(r => r.matches).length,
          results: ruleResults
        };
      });

      setTestResults(results);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test rules');
    } finally {
      setTesting(false);
    }
  };

  const handleRollback = async (version: string) => {
    if (!confirm(`Are you sure you want to rollback to version ${version}?`)) return;

    try {
      setSaving(true);
      setError(null);

      const targetVersion = versions.find(v => v.version === version);
      if (targetVersion) {
        await saveRulesToServer(targetVersion.rules);
        setRules(targetVersion.rules);
        setYamlContent(convertRulesToYaml(targetVersion.rules));
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {validationErrors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="font-medium text-red-800 mb-2">Validation Errors:</h4>
          <ul className="list-disc list-inside text-red-700 text-sm">
            {validationErrors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {conflicts.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-medium text-yellow-800 mb-2">Rule Conflicts:</h4>
          <ul className="list-disc list-inside text-yellow-700 text-sm">
            {conflicts.map((conflict, index) => (
              <li key={index}>{conflict}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Domain Rules Editor</h3>
            <p className="text-sm text-gray-600">
              Define rules that govern decision-making in this domain
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setEditMode('visual')}
                className={`px-3 py-1 text-sm rounded ${
                  editMode === 'visual' 
                    ? 'bg-white text-gray-900 shadow' 
                    : 'text-gray-600'
                }`}
              >
                Visual
              </button>
              <button
                onClick={() => setEditMode('yaml')}
                className={`px-3 py-1 text-sm rounded ${
                  editMode === 'yaml' 
                    ? 'bg-white text-gray-900 shadow' 
                    : 'text-gray-600'
                }`}
              >
                YAML
              </button>
            </div>
            
            <button
              onClick={handleTestRules}
              disabled={testing || rules.length === 0}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test Rules'}
            </button>
            
            {editMode === 'visual' && (
              <button
                onClick={handleAddRule}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Add Rule
              </button>
            )}
          </div>
        </div>

        <div className="text-sm text-gray-600">
          <p><strong>Total Rules:</strong> {rules.length}</p>
          <p><strong>Conflicts:</strong> {conflicts.length}</p>
        </div>
      </div>

      {/* Visual Editor */}
      {editMode === 'visual' && (
        <div className="space-y-4">
          {rules.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-500 mb-4">No rules defined yet.</p>
              <button
                onClick={handleAddRule}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Add Your First Rule
              </button>
            </div>
          ) : (
            rules.map((rule) => (
              <RuleCard
                key={rule.id}
                rule={rule}
                testResult={testResults[rule.id]}
                onEdit={() => handleEditRule(rule)}
                onDelete={() => handleDeleteRule(rule.id)}
                saving={saving}
              />
            ))
          )}
        </div>
      )}

      {/* YAML Editor */}
      {editMode === 'yaml' && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium">YAML Configuration</h4>
            <button
              onClick={handleYamlSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save YAML'}
            </button>
          </div>
          
          <textarea
            ref={yamlEditorRef}
            value={yamlContent}
            onChange={(e) => setYamlContent(e.target.value)}
            className="w-full h-96 px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter YAML configuration..."
          />
          
          <div className="mt-2 text-xs text-gray-500">
            <p>Use proper YAML syntax. Changes will be validated before saving.</p>
          </div>
        </div>
      )}

      {/* Version History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h4 className="font-medium mb-4">Version History</h4>
        
        {versions.length === 0 ? (
          <p className="text-gray-500">No version history available.</p>
        ) : (
          <div className="space-y-2">
            {versions.map((version) => (
              <div
                key={version.version}
                className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{version.version}</span>
                    <span className="text-sm text-gray-500">
                      by {version.author}
                    </span>
                    <span className="text-sm text-gray-500">
                      {new Date(version.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{version.changes}</p>
                </div>
                
                {version.version !== 'current' && (
                  <button
                    onClick={() => handleRollback(version.version)}
                    disabled={saving}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  >
                    Rollback
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add/Edit Rule Modal */}
      {showAddForm && editingRule && (
        <RuleEditModal
          rule={editingRule}
          onSave={handleSaveRule}
          onCancel={() => {
            setShowAddForm(false);
            setEditingRule(null);
            setValidationErrors([]);
          }}
          onChange={setEditingRule}
          saving={saving}
          validationErrors={validationErrors}
        />
      )}
    </div>
  );
};

// Rule Card Component
interface RuleCardProps {
  rule: PolicyRule;
  testResult?: any;
  onEdit: () => void;
  onDelete: () => void;
  saving: boolean;
}

const RuleCard: React.FC<RuleCardProps> = ({ 
  rule, 
  testResult, 
  onEdit, 
  onDelete, 
  saving 
}) => (
  <div className="bg-white rounded-lg shadow border-l-4 border-blue-500 p-6">
    <div className="flex items-start justify-between mb-4">
      <div className="flex-1">
        <div className="flex items-center space-x-2 mb-2">
          <h4 className="font-medium text-gray-900">{rule.id}</h4>
          {testResult && (
            <span className={`px-2 py-1 text-xs rounded ${
              testResult.matches > 0 
                ? 'bg-green-100 text-green-800' 
                : 'bg-gray-100 text-gray-600'
            }`}>
              {testResult.matches}/{testResult.totalTests} matches
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600 mb-3">{rule.description}</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h5 className="font-medium text-gray-700 mb-2">Applies When:</h5>
            <div className="bg-gray-50 rounded p-2">
              {Object.entries(rule.applies_when).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-600">{key}:</span>
                  <span className="font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div>
            <h5 className="font-medium text-gray-700 mb-2">Expect:</h5>
            <div className="bg-gray-50 rounded p-2">
              {Object.entries(rule.expect).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-600">{key}:</span>
                  <span className="font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      <div className="flex items-center space-x-1 ml-4">
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
  </div>
);

// Rule Edit Modal Component
interface RuleEditModalProps {
  rule: PolicyRule;
  onSave: () => void;
  onCancel: () => void;
  onChange: (rule: PolicyRule) => void;
  saving: boolean;
  validationErrors: string[];
}

const RuleEditModal: React.FC<RuleEditModalProps> = ({ 
  rule, 
  onSave, 
  onCancel, 
  onChange, 
  saving, 
  validationErrors 
}) => {
  const [conditionKey, setConditionKey] = useState('');
  const [conditionValue, setConditionValue] = useState('');
  const [expectationKey, setExpectationKey] = useState('');
  const [expectationValue, setExpectationValue] = useState('');

  const addCondition = () => {
    if (conditionKey && conditionValue) {
      onChange({
        ...rule,
        applies_when: {
          ...rule.applies_when,
          [conditionKey]: conditionValue
        }
      });
      setConditionKey('');
      setConditionValue('');
    }
  };

  const removeCondition = (key: string) => {
    const newConditions = { ...rule.applies_when };
    delete newConditions[key];
    onChange({
      ...rule,
      applies_when: newConditions
    });
  };

  const addExpectation = () => {
    if (expectationKey && expectationValue) {
      onChange({
        ...rule,
        expect: {
          ...rule.expect,
          [expectationKey]: expectationValue
        }
      });
      setExpectationKey('');
      setExpectationValue('');
    }
  };

  const removeExpectation = (key: string) => {
    const newExpectations = { ...rule.expect };
    delete newExpectations[key];
    onChange({
      ...rule,
      expect: newExpectations
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-medium mb-4">
          {rule.id ? 'Edit Rule' : 'Add New Rule'}
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

        <div className="space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rule ID *
              </label>
              <input
                type="text"
                value={rule.id}
                onChange={(e) => onChange({ ...rule, id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., high_confidence_approval"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description *
            </label>
            <textarea
              value={rule.description}
              onChange={(e) => onChange({ ...rule, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe when this rule applies and what it does..."
            />
          </div>

          {/* Conditions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Applies When (Conditions) *
            </label>
            
            <div className="space-y-2 mb-3">
              {Object.entries(rule.applies_when).map(([key, value]) => (
                <div key={key} className="flex items-center space-x-2 p-2 bg-gray-50 rounded">
                  <span className="font-mono text-sm">{key}:</span>
                  <span className="font-mono text-sm flex-1">{String(value)}</span>
                  <button
                    onClick={() => removeCondition(key)}
                    className="text-red-500 hover:text-red-700"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={conditionKey}
                onChange={(e) => setConditionKey(e.target.value)}
                placeholder="Key (e.g., confidence)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={conditionValue}
                onChange={(e) => setConditionValue(e.target.value)}
                placeholder="Value (e.g., >= 0.8)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addCondition}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Add
              </button>
            </div>
          </div>

          {/* Expectations */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Expect (Actions/Outcomes) *
            </label>
            
            <div className="space-y-2 mb-3">
              {Object.entries(rule.expect).map(([key, value]) => (
                <div key={key} className="flex items-center space-x-2 p-2 bg-gray-50 rounded">
                  <span className="font-mono text-sm">{key}:</span>
                  <span className="font-mono text-sm flex-1">{String(value)}</span>
                  <button
                    onClick={() => removeExpectation(key)}
                    className="text-red-500 hover:text-red-700"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={expectationKey}
                onChange={(e) => setExpectationKey(e.target.value)}
                placeholder="Key (e.g., action)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={expectationValue}
                onChange={(e) => setExpectationValue(e.target.value)}
                placeholder="Value (e.g., approve)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addExpectation}
                className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Add
              </button>
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
            {saving ? 'Saving...' : 'Save Rule'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RulesEditor;