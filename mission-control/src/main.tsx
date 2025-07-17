/**
 * Main entry point for Mission Control
 * 
 * This file bootstraps the React application and mounts it to the DOM.
 * It handles the initial setup and error boundaries.
 * 
 * Why this file exists:
 * - Bootstraps the React application
 * - Provides error boundaries for graceful error handling
 * - Sets up development tools and debugging
 * - Handles initial application configuration
 * 
 * For AI agents: This is the application bootstrap file.
 * It starts the React application and mounts it to the DOM.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// Error Boundary Component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Mission Control Error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
          <div className="text-center p-8 max-w-md">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold mb-2">Mission Control Error</h1>
            <p className="text-white/70 mb-4">
              Something went wrong. Please refresh the page or contact support.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Refresh Page
            </button>
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-4 text-left text-sm text-white/60">
                <summary className="cursor-pointer">Error Details</summary>
                <pre className="mt-2 p-2 bg-black/50 rounded overflow-auto">
                  {this.state.error?.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Get the root element
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Root element not found')
}

// Create React root
const root = ReactDOM.createRoot(rootElement)

// Render the application
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
)

// Hot Module Replacement (HMR) for development
if (process.env.NODE_ENV === 'development' && (module as any).hot) {
  (module as any).hot.accept('./App', () => {
    const NextApp = require('./App').default
    root.render(
      <React.StrictMode>
        <ErrorBoundary>
          <NextApp />
        </ErrorBoundary>
      </React.StrictMode>
    )
  })
}

// Performance monitoring
if (process.env.NODE_ENV === 'development') {
  // Log performance metrics
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      console.log('Performance:', entry.name, entry.duration)
    }
  })
  observer.observe({ entryTypes: ['measure', 'navigation'] })
}

// Global error handler
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error)
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason)
})

// Service Worker registration (if available)
if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration)
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError)
      })
  })
}