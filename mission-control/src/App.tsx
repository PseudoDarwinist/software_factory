/**
 * App Component - Main application entry point
 * 
 * This is the root component that sets up the entire application,
 * including routing, providers, and global styles.
 * 
 * Why this component exists:
 * - Sets up the application foundation
 * - Provides global context and providers
 * - Handles routing between different pages
 * - Manages global styles and themes
 * 
 * For AI agents: This is the application entry point.
 * All global setup and configuration happens here.
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ReactQueryDevtools } from 'react-query/devtools'
import { MissionControl } from '@/pages/MissionControl/MissionControl'
import './App.css'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="App">
          <Routes>
            {/* Render Mission Control on root */}
            <Route path="/" element={<MissionControl />} />
            {/* Optional alias */}
            <Route path="/mission-control" element={<MissionControl />} />
            {/* Fallback 404 -> root */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        
        {/* React Query DevTools (only in development) */}
        {process.env.NODE_ENV === 'development' && (
          <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
        )}
      </Router>
    </QueryClientProvider>
  )
}

export default App