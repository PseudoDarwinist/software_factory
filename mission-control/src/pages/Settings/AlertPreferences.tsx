import React from 'react'
import { useNotificationPrefs, useActions } from '@/stores/missionControlStore'

export const AlertPreferences: React.FC = () => {
  const prefs = useNotificationPrefs()
  const { setNotificationPrefs, enableBrowserNotifications } = useActions()

  return (
    <div className="space-y-4">
      <div className="bg-white/5 border border-white/10 rounded-lg p-4">
        <h4 className="font-medium mb-2">Toast Notifications</h4>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={prefs.toastsEnabled} onChange={(e) => setNotificationPrefs({ toastsEnabled: e.target.checked })} />
            <span className="text-sm">Enable toast notifications</span>
          </label>
          <div className="flex items-center gap-4 ml-6">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={prefs.showSuccess} onChange={(e) => setNotificationPrefs({ showSuccess: e.target.checked })} />
              <span className="text-sm">Show success</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={prefs.showWarnings} onChange={(e) => setNotificationPrefs({ showWarnings: e.target.checked })} />
              <span className="text-sm">Show warnings</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={prefs.showErrors} onChange={(e) => setNotificationPrefs({ showErrors: e.target.checked })} />
              <span className="text-sm">Show errors</span>
            </label>
          </div>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-lg p-4">
        <h4 className="font-medium mb-2">Browser Notifications</h4>
        <p className="text-sm text-white/70 mb-3">Enable native browser notifications for critical events.</p>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1.5 rounded border text-sm hover:bg-white/10"
            onClick={enableBrowserNotifications}
          >
            Enable
          </button>
          <span className="text-xs text-white/60">{prefs.browserNotifications ? 'Enabled' : 'Disabled'}</span>
        </div>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-lg p-4">
        <h4 className="font-medium mb-2">Sound Alerts</h4>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={prefs.soundEnabled} onChange={(e) => setNotificationPrefs({ soundEnabled: e.target.checked })} />
          <span className="text-sm">Enable sound for critical failures</span>
        </label>
      </div>
    </div>
  )
}

export default AlertPreferences