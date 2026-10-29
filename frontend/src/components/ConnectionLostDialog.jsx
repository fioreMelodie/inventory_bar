import { useEffect, useRef } from 'react'
import { WifiOff } from 'lucide-react'

export default function ConnectionLostDialog({ onConfirm }) {
  const dialog = useRef(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return (
    <dialog ref={dialog} className="confirmation-dialog" aria-labelledby="connection-lost-title" aria-describedby="connection-lost-description"
      onCancel={event => event.preventDefault()}>
      <span className="dialog-symbol"><WifiOff size={24} /></span>
      <h2 id="connection-lost-title">Connection lost</h2>
      <p id="connection-lost-description">
        Your internet connection is unavailable. Your order has been saved and no data was
        lost. You will be signed out and can continue once the connection is restored.
      </p>
      <button type="button" onClick={onConfirm} autoFocus className="primary-button mt-6 w-full">Understood</button>
    </dialog>
  )
}
