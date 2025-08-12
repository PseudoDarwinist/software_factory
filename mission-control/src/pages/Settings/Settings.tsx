/**
 * Settings Page - Main settings page with monitoring dashboard
 * 
 * This page provides access to system monitoring and configuration.
 * It includes the monitoring dashboard as the primary tab.
 * 
 * Why this page exists:
 * - Provides centralized access to system settings and monitoring
 * - Implements the monitoring dashboard as specified in the design
 * - Maintains consistent navigation and layout with Mission Control
 * 
 * For AI agents: This is the main settings page that houses the monitoring dashboard.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import { MonitoringDashboard } from '@/components/monitoring/MonitoringDashboard'
import { HealthPill } from '@/components/monitoring/HealthPill'
import type { SystemHealth } from '@/types/monitoring'
import { AlertPreferences } from './AlertPreferences'

interface SettingsProps {
  onBack?: () => void
}

type SettingsTab = 'monitoring' | 'agents' | 'integrations' | 'alerts'

export const Settings: React.FC<SettingsProps> = ({ onBack }) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('monitoring')
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const navigate = useNavigate()

  // Load system health for header pill
  useEffect(() => {
    const loadSystemHealth = async () => {
      try {
        const response = await fetch('/api/monitoring/metrics')
        if (response.ok) {
          const metrics = await response.json()
          // Extract system health from metrics response
          const systemHealth = metrics.system_health
          if (systemHealth) {
            // Add status field based on overall score
            systemHealth.status = systemHealth.overall_score >= 80 ? 'healthy' : 
                                 systemHealth.overall_score >= 50 ? 'warning' : 'critical'
            setSystemHealth(systemHealth)
          }
        }
      } catch (error) {
        console.error('Failed to load system health:', error)
        // Set fallback health status
        setSystemHealth({
          overallScore: 0,
          status: 'critical',
          components: {},
          resources: {},
          performance: {}
        })
      }
    }

    loadSystemHealth()
    
    // Refresh health every 30 seconds
    const interval = setInterval(loadSystemHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const tabs: Array<{ id: SettingsTab; label: string; icon: string; available: boolean }> = [
    { id: 'monitoring', label: 'Monitoring', icon: '📊', available: true },
    { id: 'agents', label: 'Agents', icon: '🤖', available: false },
    { id: 'integrations', label: 'Integrations', icon: '🔗', available: false },
    { id: 'alerts', label: 'Alerts', icon: '🚨', available: true },
  ]

  return (
    <div className="h-screen bg-black text-white overflow-hidden">
      {/* Header */}
      <div className="h-16 bg-black/20 backdrop-blur-md border-b border-white/10 flex items-center justify-between px-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack || (() => navigate('/'))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
            title="Back to Mission Control"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-xl font-semibold">Settings</h1>
        </div>
        
        {/* System Health Pill */}
        <div className="flex items-center space-x-4">
          {systemHealth && (
            <HealthPill 
              health={systemHealth} 
              showLabel={true}
            />
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="h-12 bg-black/10 backdrop-blur-sm border-b border-white/5 flex items-center px-6">
        <div className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => tab.available && setActiveTab(tab.id)}
              disabled={!tab.available}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                'flex items-center space-x-2',
                activeTab === tab.id
                  ? 'bg-white/10 text-white border border-white/20'
                  : tab.available
                  ? 'text-white/70 hover:text-white hover:bg-white/5'
                  : 'text-white/30 cursor-not-allowed'
              )}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {!tab.available && (
                <span className="text-xs text-white/40">(Soon)</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {activeTab === 'monitoring' && (
            <motion.div
              key="monitoring"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <MonitoringDashboard />
            </motion.div>
          )}
          
          {activeTab === 'agents' && (
            <motion.div
              key="agents"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full flex items-center justify-center"
            >
              <div className="text-center text-white/60">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                  <span className="text-white/40 text-2xl">🤖</span>
                </div>
                <h3 className="text-lg font-medium mb-2">Agent Configuration</h3>
                <p className="text-sm">Coming soon - Agent management and configuration</p>
              </div>
            </motion.div>
          )}
          
          {activeTab === 'integrations' && (
            <motion.div
              key="integrations"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full flex items-center justify-center"
            >
              <div className="text-center text-white/60">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                  <span className="text-white/40 text-2xl">🔗</span>
                </div>
                <h3 className="text-lg font-medium mb-2">Integration Settings</h3>
                <p className="text-sm">Coming soon - External service configuration</p>
              </div>
            </motion.div>
          )}
          
          {activeTab === 'alerts' && (
            <motion.div
              key="alerts"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <div className="max-w-3xl mx-auto p-6 space-y-6">
                <h3 className="text-lg font-semibold">Alert & Notification Preferences</h3>
                <AlertPreferences />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Grid Paper Background */}
      <div className="fixed inset-0 pointer-events-none -z-10">
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              repeating-linear-gradient(
                to right,
                transparent 0 59px,
                rgba(255,255,255,.03) 59px 60px
              ),
              repeating-linear-gradient(
                to bottom,
                transparent 0 59px,
                rgba(255,255,255,.03) 59px 60px
              )
            `,
            backgroundColor: '#151821',
          }}
        />
      </div>
    </div>
  )
}

export default Settings