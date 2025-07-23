/**
 * AnalyticsCharts Component - Clean version without Global Impact and Network Throughput
 */

import React from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { DashboardMetrics } from '@/types/monitoring'

interface AnalyticsChartsProps {
  metrics: DashboardMetrics
}

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ metrics }) => {
  // Generate time series data for the last 24 hours
  const generateTimeSeriesData = () => {
    const data = []
    const now = new Date()
    
    for (let i = 23; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000)
      data.push({
        time: time.getHours().toString().padStart(2, '0') + ':00',
        events: Math.floor(Math.random() * 30) + 40,
        errors: Math.floor(Math.random() * 8) + 2,
        responseTime: Math.floor(Math.random() * 200) + 100,
        success: Math.floor(Math.random() * 50) + 80,
      })
    }
    return data
  }

  const timeSeriesData = generateTimeSeriesData()

  const colors = {
    blue: '#2F79FF',
    orange: '#FFB547', 
    green: '#19C37D',
    red: '#FF5454',
  }

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/80 backdrop-blur-sm rounded-lg p-3 border border-white/20">
          <p className="text-white/80 text-sm mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="card space-y-6"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Analytics</h3>
        <div className="text-xs text-white/60">
          Last 24 hours
        </div>
      </div>

      {/* Event Volume Chart */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-white/80">Event Volume</h4>
        <div className="h-48 chart-mesh">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeSeriesData}>
              <defs>
                <linearGradient id="eventsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.blue} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={colors.blue} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.08)" />
              <XAxis 
                dataKey="time" 
                stroke="rgba(255,255,255,0.6)"
                fontSize={12}
                tickLine={false}
              />
              <YAxis 
                stroke="rgba(255,255,255,0.6)"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="events"
                stroke={colors.blue}
                fillOpacity={1}
                fill="url(#eventsGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Row - Three Colored Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Error Rate Spike - Red */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-white/80 uppercase tracking-wide">Error rate spike</h4>
            <span className="text-red-400 text-xs flex items-center">
              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Critical
            </span>
          </div>
          <div className="h-48 chart-mesh">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="errorGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors.red} stopOpacity={0.4}/>
                    <stop offset="95%" stopColor={colors.red} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.08)" />
                <XAxis hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="errors"
                  stroke={colors.red}
                  fillOpacity={1}
                  fill="url(#errorGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Response Time - Orange */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-white/80 uppercase tracking-wide">Response time (ms)</h4>
          </div>
          <div className="h-48 chart-mesh">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="responseGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors.orange} stopOpacity={0.4}/>
                    <stop offset="95%" stopColor={colors.orange} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.08)" />
                <XAxis hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="responseTime"
                  stroke={colors.orange}
                  fillOpacity={1}
                  fill="url(#responseGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Request Success - Green */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-white/80 uppercase tracking-wide">Request success</h4>
          </div>
          <div className="h-48 chart-mesh">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeSeriesData}>
                <defs>
                  <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors.green} stopOpacity={0.4}/>
                    <stop offset="95%" stopColor={colors.green} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.08)" />
                <XAxis hide />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="success"
                  stroke={colors.green}
                  fillOpacity={1}
                  fill="url(#successGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default AnalyticsCharts