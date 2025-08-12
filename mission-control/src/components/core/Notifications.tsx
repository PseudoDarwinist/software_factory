import React, { useEffect, useRef } from 'react'
import { useMissionControlStore } from '@/stores/missionControlStore'
import { useNotificationPrefs } from '@/stores/missionControlStore'

function playErrorBeep() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.type = 'sawtooth'
    o.frequency.setValueAtTime(520, ctx.currentTime)
    g.gain.setValueAtTime(0.001, ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.08, ctx.currentTime + 0.02)
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.25)
    o.connect(g)
    g.connect(ctx.destination)
    o.start()
    o.stop(ctx.currentTime + 0.28)
  } catch {}
}

export const Notifications: React.FC = () => {
  const notifications = useMissionControlStore((s) => s.notifications)
  const remove = useMissionControlStore((s) => s.actions.removeNotification)
  const prefs = useNotificationPrefs()
  const playedRef = useRef<Set<string>>(new Set())

  // Auto-close timers
  useEffect(() => {
    if (!prefs.toastsEnabled) return
    const timers: number[] = []
    notifications.forEach((n) => {
      if (n.autoClose !== false) {
        const t = window.setTimeout(() => remove(n.id), n.duration ?? 4000)
        timers.push(t)
      }
    })
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [notifications, prefs.toastsEnabled])

  // Sound on critical errors
  useEffect(() => {
    if (!prefs.soundEnabled) return
    for (const n of notifications) {
      if (n.type === 'error' && !playedRef.current.has(n.id)) {
        playErrorBeep()
        playedRef.current.add(n.id)
      }
    }
  }, [notifications, prefs.soundEnabled])

  if (!prefs.toastsEnabled) return null

  // Filter by type preferences
  const filtered = notifications.filter((n) => {
    if (n.type === 'success' && !prefs.showSuccess) return false
    if (n.type === 'warning' && !prefs.showWarnings) return false
    if (n.type === 'error' && !prefs.showErrors) return false
    return true
  })

  if (!filtered.length) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {filtered.map((n) => (
        <div
          key={n.id}
          className="min-w-[280px] max-w-[360px] rounded-lg border p-3 shadow-lg backdrop-blur-md"
          style={{
            background: 'rgba(12,17,25,0.8)',
            borderColor: 'rgba(255,255,255,0.12)',
          }}
        >
          <div className="flex items-start gap-3">
            <div className="text-xl select-none">
              {n.type === 'success' ? '✅' : n.type === 'error' ? '❌' : n.type === 'warning' ? '⚠️' : 'ℹ️'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-medium text-sm mb-1 truncate">{n.title}</div>
              <div className="text-white/70 text-xs leading-relaxed">{n.message}</div>
              {n.actions && n.actions.length > 0 && (
                <div className="mt-2 flex gap-2 flex-wrap">
                  {n.actions.map((a, idx) => (
                    <button
                      key={idx}
                      className="px-2 py-1 rounded border text-xs text-white/80 hover:bg-white/10"
                      onClick={() => remove(n.id)}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="text-white/50 hover:text-white/80" onClick={() => remove(n.id)}>
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default Notifications

