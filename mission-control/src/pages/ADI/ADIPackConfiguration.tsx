import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { adiApi } from '../../services/api/adiApi';
import { DomainPack } from '../../types/adi';
import PackMetadataEditor from '../../components/adi/PackMetadataEditor';
import MetricsConfiguration from '../../components/adi/MetricsConfiguration';
import OntologyBuilder from '../../components/adi/OntologyBuilder';
import RulesEditor from '../../components/adi/RulesEditor';
import KnowledgeManager from '../../components/adi/KnowledgeManager';

interface ConfigSection {
  id: string;
  label: string;
  icon: string;
  component: React.ComponentType<{ projectId: string; pack: DomainPack | null; onUpdate?: (pack: DomainPack) => void }>;
}

const ADIPackConfiguration: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [pack, setPack] = useState<DomainPack | null>(null);
  const [activeSection, setActiveSection] = useState('metadata');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const configSections: ConfigSection[] = [
    {
      id: 'metadata',
      label: 'Pack Metadata',
      icon: '📋',
      component: PackMetadataEditor
    },
    {
      id: 'metrics',
      label: 'Metrics & KPIs',
      icon: '📊',
      component: MetricsConfiguration
    },
    {
      id: 'ontology',
      label: 'Failure Modes',
      icon: '🏗️',
      component: OntologyBuilder
    },
    {
      id: 'rules',
      label: 'Domain Rules',
      icon: '📝',
      component: RulesEditor
    },
    {
      id: 'knowledge',
      label: 'Knowledge Base',
      icon: '🧠',
      component: KnowledgeManager
    }
  ];

  useEffect(() => {
    if (projectId) {
      loadDomainPack();
    }
  }, [projectId]);

  const loadDomainPack = async () => {
    try {
      setLoading(true);
      const packData = await adiApi.getDomainPack(projectId!);
      setPack(packData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load domain pack');
    } finally {
      setLoading(false);
    }
  };

  const ActiveComponent = configSections.find(s => s.id === activeSection)?.component || PackMetadataEditor;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error}</p>
        <button 
          onClick={loadDomainPack}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar Navigation */}
      <div className="w-64 bg-white shadow-sm border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-semibold text-gray-900">Domain Pack Configuration</h1>
          {pack && (
            <p className="text-sm text-gray-600 mt-1">
              {pack.name} v{pack.version}
            </p>
          )}
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {configSections.map((section) => (
              <li key={section.id}>
                <button
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <span className="mr-3">{section.icon}</span>
                  {section.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Pack Status */}
        <div className="p-4 border-t border-gray-200">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span>Status</span>
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded">Active</span>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-600 mt-2">
              <span>Last Updated</span>
              <span>{pack?.updated_at ? new Date(pack.updated_at).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-gray-900">
                {configSections.find(s => s.id === activeSection)?.label}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Configure your domain pack settings
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                Preview Changes
              </button>
              <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700">
                Deploy Pack
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <ActiveComponent projectId={projectId!} pack={pack} onUpdate={setPack} />
        </div>
      </div>
    </div>
  );
};



export default ADIPackConfiguration;