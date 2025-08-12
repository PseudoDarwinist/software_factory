import React, { useState, useEffect } from 'react';
import { DomainPack } from '../../types/adi';
import { adiApi } from '../../services/api/adiApi';

interface PackMetadataEditorProps {
  projectId: string;
  pack: DomainPack | null;
  onUpdate?: (pack: DomainPack) => void;
}

const PackMetadataEditor: React.FC<PackMetadataEditorProps> = ({ 
  projectId, 
  pack, 
  onUpdate 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    version: '',
    owner_team: '',
    description: '',
    extends: ''
  });
  const [versions, setVersions] = useState<Array<{ version: string; deployed_at: string; status: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (pack) {
      setFormData({
        name: pack.name || '',
        version: pack.version || '',
        owner_team: pack.owner_team || '',
        description: pack.description || '',
        extends: pack.extends || ''
      });
    }
    loadVersions();
  }, [pack]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      const versionData = await adiApi.getPackVersions(projectId);
      setVersions(versionData);
    } catch (err) {
      console.error('Failed to load versions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const updatedPack = await adiApi.updateDomainPack(projectId, formData);
      onUpdate?.(updatedPack);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save pack metadata');
    } finally {
      setSaving(false);
    }
  };

  const handleDeploy = async () => {
    try {
      setSaving(true);
      setError(null);
      
      await adiApi.deployDomainPack(projectId, formData.version);
      await loadVersions();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deploy pack');
    } finally {
      setSaving(false);
    }
  };

  const handleRollback = async (version: string) => {
    if (!confirm(`Are you sure you want to rollback to version ${version}?`)) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      
      await adiApi.rollbackDomainPack(projectId, version);
      await loadVersions();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback pack');
    } finally {
      setSaving(false);
    }
  };

  const incrementVersion = (type: 'major' | 'minor' | 'patch') => {
    const parts = formData.version.split('.').map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) {
      setFormData(prev => ({ ...prev, version: '1.0.0' }));
      return;
    }

    switch (type) {
      case 'major':
        parts[0]++;
        parts[1] = 0;
        parts[2] = 0;
        break;
      case 'minor':
        parts[1]++;
        parts[2] = 0;
        break;
      case 'patch':
        parts[2]++;
        break;
    }

    setFormData(prev => ({ ...prev, version: parts.join('.') }));
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Basic Metadata */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium mb-4">Basic Information</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Pack Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., IROPS - Irregular Operations"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Owner Team
            </label>
            <input
              type="text"
              value={formData.owner_team}
              onChange={(e) => handleInputChange('owner_team', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., operations"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe what this domain pack handles..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Extends Pack (Optional)
            </label>
            <input
              type="text"
              value={formData.extends}
              onChange={(e) => handleInputChange('extends', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., _default"
            />
          </div>
        </div>
      </div>

      {/* Version Management */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium mb-4">Version Management</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current Version
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={formData.version}
                onChange={(e) => handleInputChange('version', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1.0.0"
              />
              <button
                onClick={() => incrementVersion('patch')}
                className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                +Patch
              </button>
              <button
                onClick={() => incrementVersion('minor')}
                className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                +Minor
              </button>
              <button
                onClick={() => incrementVersion('major')}
                className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                +Major
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              onClick={handleDeploy}
              disabled={saving}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? 'Deploying...' : 'Deploy Version'}
            </button>
          </div>
        </div>
      </div>

      {/* Version History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium mb-4">Version History</h3>
        
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>
        ) : versions.length === 0 ? (
          <p className="text-gray-500 py-4">No versions deployed yet.</p>
        ) : (
          <div className="space-y-2">
            {versions.map((version, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <span className="font-medium">{version.version}</span>
                  <span className={`px-2 py-1 text-xs rounded ${
                    version.status === 'active' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {version.status}
                  </span>
                  <span className="text-sm text-gray-500">
                    {new Date(version.deployed_at).toLocaleDateString()}
                  </span>
                </div>
                
                {version.status !== 'active' && (
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
    </div>
  );
};

export default PackMetadataEditor;