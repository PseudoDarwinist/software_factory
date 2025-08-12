import React, { useState } from 'react'
import ConfirmDialog from './ConfirmDialog'

interface ActionButtonsProps {
  onApproveOverride: (reason?: string) => Promise<void> | void
  onSendToBug: (reason?: string) => Promise<void> | void
  onReject?: (reason?: string) => Promise<void> | void
  onRetry?: (debug?: boolean) => Promise<void> | void
  canApprove?: boolean
  canOverride?: boolean
  canBug?: boolean
  canReject?: boolean
  canRetry?: boolean
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onApproveOverride,
  onSendToBug,
  onReject,
  onRetry,
  canApprove = true,
  canOverride = true,
  canBug = true,
  canReject = true,
  canRetry = true,
}) => {
  const [confirm, setConfirm] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void }>({ open: false, title: '', message: '', onConfirm: () => {} })
  const [reason, setReason] = useState('')

  const ask = (title: string, message: string, onConfirm: () => void) => setConfirm({ open: true, title, message, onConfirm })

  return (
    <div className="space-y-2">
      <textarea
        className="w-full bg-white/5 border border-white/10 rounded p-2 text-sm text-white/80"
        placeholder="Add an optional reason or comment..."
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="flex items-center gap-2">
        {canApprove && (
          <button
            className="bg-green-500/20 border border-green-500/30 text-green-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-green-500/30 transition-colors"
            onClick={() => ask('Approve Override', 'Confirm approving this validation with override?', async () => { await onApproveOverride(reason); setConfirm({ ...confirm, open: false }) })}
          >
            ✓ Approve Override
          </button>
        )}
        {canBug && (
          <button
            className="bg-blue-500/20 border border-blue-500/30 text-blue-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-500/30 transition-colors"
            onClick={() => ask('Send to Bug Tracking', 'Create a bug and attach evidence?', async () => { await onSendToBug(reason); setConfirm({ ...confirm, open: false }) })}
          >
            🐛 Send to Bug Tracking
          </button>
        )}
        {canReject && onReject && (
          <button
            className="bg-red-500/20 border border-red-500/30 text-red-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-red-500/30 transition-colors"
            onClick={() => ask('Reject', 'Reject this validation?', async () => { await onReject(reason); setConfirm({ ...confirm, open: false }) })}
          >
            ✗ Reject
          </button>
        )}
        {canRetry && onRetry && (
          <button
            className="bg-amber-500/20 border border-amber-500/30 text-amber-300 py-2 px-4 rounded-lg text-sm font-medium hover:bg-amber-500/30 transition-colors"
            onClick={() => ask('Retry', 'Retry this validation (optionally in debug mode)?', async () => { await onRetry(true); setConfirm({ ...confirm, open: false }) })}
          >
            🔄 Retry (Debug)
          </button>
        )}
      </div>

      <ConfirmDialog
        open={confirm.open}
        title={confirm.title}
        message={confirm.message}
        onConfirm={confirm.onConfirm}
        onCancel={() => setConfirm({ ...confirm, open: false })}
      />
    </div>
  )
}

export default ActionButtons

