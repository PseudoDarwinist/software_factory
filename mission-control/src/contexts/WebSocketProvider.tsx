import React, { createContext, useContext, useEffect, useState } from 'react'
import validationWS, { type WebSocketConnectionStatus } from '@/services/validation/validationWebSocket'

interface WebSocketContextValue {
  status: WebSocketConnectionStatus
}

const WebSocketContext = createContext<WebSocketContextValue>({
  status: { connected: false, connecting: false, error: null, lastConnected: null, reconnectAttempts: 0 },
})

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<WebSocketConnectionStatus>({
    connected: false,
    connecting: false,
    error: null,
    lastConnected: null,
    reconnectAttempts: 0,
  })

  useEffect(() => {
    validationWS.connect().catch(() => {})
    const unsub = validationWS.onStatusChange(setStatus)
    return () => {
      unsub()
    }
  }, [])

  return (
    <WebSocketContext.Provider value={{ status }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocketContext = () => useContext(WebSocketContext)

export default WebSocketProvider

