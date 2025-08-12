import React, { useState, useEffect } from 'react';
import { DomainPack, MetricConfig } from '../../types/adi';
import { adiApi } from '../../services/api/adiApi';

interface MetricsConfigurationProps {
  projectId: string;
  pack: DomainPack | null;
  onUpdate?: (pack: DomainPack) => void;
}

const MetricsConfiguration: React.FC<MetricsConfigurationProps> = ({ 
  projectId, 
  pack, 
  onUpdate 
}) => {
  const [metrics, setMetrics] = useState<MetricConfig[]>([]);
  const [editingMetric, setEditingMetric] = useState<MetricConfig | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{ [key: string]: any }>({});

  useEffect(() => {
    if (pack?.pack_data?.metrics) {
      setMetrics(pack.pack_data.metrics);
    }
  }, [pack]);

  const handleAddMetric = () => {
    const newMetric: MetricConfig = {
      key: '',
      label: '',
      description: '',
      type: 'supporting',
      compute: '',
      target: undefined,
      unit: ''
    };
    setEditingMetric(newMetric);
    setShowAddForm(true);
  };

  const handleEditMetric = (metric: MetricConfig) => {
    setEditingMetric({ ...metric });
    setShowAddForm(true);
  };

  const handleSaveMetric = async () => {
    if (!editingMetric) return;

    // Validate metric
    const errors = validateMetric(editingMetric);
    if (errors.length > 0) {
      setError(errors.join(', '));
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // Update metrics list
      const updatedMetrics = editingMetric.key && metrics.find(m => m.key === editingMetric.key)
        ? metrics.map(m => m.key === editingMetric.key ? editingMetric : m)
        : [...metrics, editingMetric];

      // Update pack
      const updatedPack = await adiApi.updateDomainPack(projectId, {
        pack_data: {
          ...pack?.pack_data,
          metrics: updatedMetrics
        }
      });

      setMetrics(updatedMetrics);
      onUpdate?.(updatedPack);
      setShowAddForm(false);
      setEditingMetric(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save metric');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMetric = async (metricKey: string) => {
    if (!confirm('Are you sure you want to delete this metric?')) return;

    try {
      setSaving(true);
      setError(null);

      const updatedMetrics = metrics.filter(m => m.key !== metricKey);

      const updatedPack = await adiApi.updateDomainPack(projectId, {
        pack_data: {
          ...pack?.pack_data,
          metrics: updatedMetrics
        }
      });

      setMetrics(updatedMetrics);
      onUpdate?.(updatedPack);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete metric');
    } finally {
      setSaving(false);
    }
  };

  const validateMetric = (metric: MetricConfig): string[] => {
    const errors: string[] = [];
    
    if (!metric.key.trim()) errors.push('Key is required');
    if (!metric.label.trim()) errors.push('Label is required');
    if (!metric.description.trim()) errors.push('Description is required');
    if (!metric.compute.trim()) errors.push('Compute method is required');
    
    // Check for duplicate keys
    if (metrics.some(m => m.key === metric.key && m !== editingMetric)) {
      errors.push('Key must be unique');
    }

    return errors;
  };

  const handlePreviewMetric = async (metric: MetricConfig) => {
    try {
      // Mock preview data - in real implementation, this would call the backend
      const mockData = {
        current_value: Math.random() * 100,
        trend: Math.random() > 0.5 ? 'up' : 'down',
        last_updated: new Date().toISOString()
      };
      
      setPreviewData(prev => ({
        ...prev,
        [metric.key]: mockData
      }));
    } catch (err) {
      console.error('Failed to preview metric:', err);
    }
  };

  const northStarMetrics = metrics.filter(m => m.type === 'north_star');
  const supportingMetrics = metrics.filter(m => m.type === 'supporting');

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* North Star Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">North Star Metrics</h3>
            <p className="text-sm text-gray-600">Primary success indicators for this domain</p>
          </div>
          <button
            onClick={() => {
              const newMetric: MetricConfig = {
                key: '',
                label: '',
                description: '',
                type: 'north_star',
                compute: '',
                target: undefined,
                unit: ''
              };
              setEditingMetric(newMetric);
              setShowAddForm(true);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Add North Star Metric
          </button>
        </div>

        {northStarMetrics.length === 0 ? (
          <p className="text-gray-500 py-4">No north star metrics defined yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {northStarMetrics.map((metric) => (
              <MetricCard
                key={metric.key}
                metric={metric}
                preview={previewData[metric.key]}
                onEdit={() => handleEditMetric(metric)}
                onDelete={() => handleDeleteMetric(metric.key)}
                onPreview={() => handlePreviewMetric(metric)}
                saving={saving}
              />
            ))}
          </div>
        )}
      </div>

      {/* Supporting Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Supporting Metrics</h3>
            <p className="text-sm text-gray-600">Additional metrics that provide context and insights</p>
          </div>
          <button
            onClick={() => {
              const newMetric: MetricConfig = {
                key: '',
                label: '',
                description: '',
                type: 'supporting',
                compute: '',
                target: undefined,
                unit: ''
              };
              setEditingMetric(newMetric);
              setShowAddForm(true);
            }}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Add Supporting Metric
          </button>
        </div>

        {supportingMetrics.length === 0 ? (
          <p className="text-gray-500 py-4">No supporting metrics defined yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {supportingMetrics.map((metric) => (
              <MetricCard
                key={metric.key}
                metric={metric}
                preview={previewData[metric.key]}
                onEdit={() => handleEditMetric(metric)}
                onDelete={() => handleDeleteMetric(metric.key)}
                onPreview={() => handlePreviewMetric(metric)}
                saving={saving}
              />
            ))}
          </div>
        )}
      </div>

      {/* Add/Edit Metric Modal */}
      {showAddForm && editingMetric && (
        <MetricEditModal
          metric={editingMetric}
          onSave={handleSaveMetric}
          onCancel={() => {
            setShowAddForm(false);
            setEditingMetric(null);
            setError(null);
          }}
          onChange={setEditingMetric}
          saving={saving}
        />
      )}
    </div>
  );
};

interface MetricCardProps {
  metric: MetricConfig;
  preview?: any;
  onEdit: () => void;
  onDelete: () => void;
  onPreview: () => void;
  saving: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  metric, 
  preview, 
  onEdit, 
  onDelete, 
  onPreview, 
  saving 
}) => (
  <div className={`border rounded-lg p-4 ${
    metric.type === 'north_star' 
      ? 'border-blue-200 bg-blue-50' 
      : 'border-gray-200 bg-gray-50'
  }`}>
    <div className="flex items-start justify-between mb-2">
      <div className="flex-1">
        <h4 className="font-medium text-gray-900">{metric.label}</h4>
        <p className="text-sm text-gray-600 mt-1">{metric.description}</p>
        <div className="flex items-center space-x-2 mt-2">
          <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
            {metric.key}
          </span>
          {metric.target && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
              Target: {metric.target}{metric.unit}
            </span>
          )}
        </div>
      </div>
      
      <div className="flex items-center space-x-1 ml-2">
        <button
          onClick={onPreview}
          className="p-1 text-gray-400 hover:text-gray-600"
          title="Preview"
        >
          👁️
        </button>
        <button
          onClick={onEdit}
          disabled={saving}
          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
          title="Edit"
        >
          ✏️
        </button>
        <button
          onClick={onDelete}
          disabled={saving}
          className="p-1 text-red-400 hover:text-red-600 disabled:opacity-50"
          title="Delete"
        >
          🗑️
        </button>
      </div>
    </div>

    {preview && (
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Current Value:</span>
          <span className="font-medium">
            {preview.current_value?.toFixed(2)}{metric.unit}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm mt-1">
          <span className="text-gray-600">Trend:</span>
          <span className={`font-medium ${
            preview.trend === 'up' ? 'text-green-600' : 'text-red-600'
          }`}>
            {preview.trend === 'up' ? '↗️' : '↘️'} {preview.trend}
          </span>
        </div>
      </div>
    )}

    <div className="mt-3 text-xs text-gray-500">
      <strong>Compute:</strong> {metric.compute}
    </div>
  </div>
);

interface MetricEditModalProps {
  metric: MetricConfig;
  onSave: () => void;
  onCancel: () => void;
  onChange: (metric: MetricConfig) => void;
  saving: boolean;
}

const MetricEditModal: React.FC<MetricEditModalProps> = ({ 
  metric, 
  onSave, 
  onCancel, 
  onChange, 
  saving 
}) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <h3 className="text-lg font-medium mb-4">
        {metric.key ? 'Edit Metric' : 'Add New Metric'}
      </h3>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Key *
            </label>
            <input
              type="text"
              value={metric.key}
              onChange={(e) => onChange({ ...metric, key: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., accuracy_rate"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type *
            </label>
            <select
              value={metric.type}
              onChange={(e) => onChange({ ...metric, type: e.target.value as 'north_star' | 'supporting' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="north_star">North Star</option>
              <option value="supporting">Supporting</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Label *
          </label>
          <input
            type="text"
            value={metric.label}
            onChange={(e) => onChange({ ...metric, label: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Decision Accuracy Rate"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            value={metric.description}
            onChange={(e) => onChange({ ...metric, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Describe what this metric measures and why it's important..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Compute Method *
          </label>
          <select
            value={metric.compute}
            onChange={(e) => onChange({ ...metric, compute: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select computation method...</option>
            <option value="correctness_rate">Correctness Rate</option>
            <option value="confidence_avg">Average Confidence</option>
            <option value="response_time_p95">95th Percentile Response Time</option>
            <option value="failure_rate">Failure Rate</option>
            <option value="throughput">Throughput (requests/min)</option>
            <option value="custom_sql">Custom SQL Query</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Value
            </label>
            <input
              type="number"
              step="0.01"
              value={metric.target || ''}
              onChange={(e) => onChange({ ...metric, target: e.target.value ? parseFloat(e.target.value) : undefined })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., 95"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Unit
            </label>
            <input
              type="text"
              value={metric.unit || ''}
              onChange={(e) => onChange({ ...metric, unit: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., %, ms, requests"
            />
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
          {saving ? 'Saving...' : 'Save Metric'}
        </button>
      </div>
    </div>
  </div>
);

export default MetricsConfiguration;