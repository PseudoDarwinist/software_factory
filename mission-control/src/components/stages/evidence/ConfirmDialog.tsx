import React from 'react'

interface ConfirmDialogProps {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  open: boolean
  onConfirm: () => void
  onCancel: () => void
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  open,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-slate-900/90 backdrop-blur border border-white/10 rounded-lg p-5 w-full max-w-md">
        <h3 className="text-white font-semibold mb-2">{title}</h3>
        <p className="text-white/70 text-sm mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded border border-white/10 bg-white/5 text-white/80 hover:bg-white/10 text-sm">{cancelText}</button>
          <button onClick={onConfirm} className="px-3 py-1.5 rounded border border-green-500/40 bg-green-500/20 text-green-300 hover:bg-green-500/30 text-sm">{confirmText}</button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog

