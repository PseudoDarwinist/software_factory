import React from 'react'
import { TrendsDashboard } from './trends/TrendsDashboard'

export const TrendsPanel: React.FC = () => {
  return (
    <div className="h-full p-4">
      <TrendsDashboard />
    </div>
  )
}

export default TrendsPanel

