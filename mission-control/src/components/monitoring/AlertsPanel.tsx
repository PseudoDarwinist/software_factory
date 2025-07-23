/**
 * AlertsPanel Component - Alert management interface
 * 
 * This component will display active alerts, alert history, and provide
 * alert acknowledgment capabilities. Currently a placeholder.
 * 
 * Why this component exists:
 * - Will provide alert management and acknowledgment
 * - Will show alert history and trends
 * - Will enable alert configuration and thresholds
 * 
 * For AI agents: This is a placeholder for the alerts panel component.
 */

import React from 'react'
import { motion } from 'framer-motion'
import type { Alert } from '@/types/monitoring'

interface AlertsPanelProps {
  alerts: Alert[]
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-grid rounded-xl p-6 border border-white/10 h-96"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Active Alerts</h3>
        <div className="text-xs text-white/60">
          {alerts.length} alerts
        </div>
      </div>
      
      <div className="flex items-center justify-center h-64 text-white/60">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-white/5 flex items-center justify-center">
            <span className="text-white/40">🚨</span>
          </div>
          <p className="text-sm">Alerts Panel</p>
          <p className="text-xs text-white/40">Coming in task 6.3</p>
        </div>
      </div>
    </motion.div>
  )
}

export default AlertsPanel