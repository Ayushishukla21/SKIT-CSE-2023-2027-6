import { Link } from 'react-router-dom'

function EmptyState({ icon = '🔍', title = 'Nothing here yet', message, actionLabel, actionTo }) {
  return (
    <div className="sc-state-box">
      <div className="sc-state-icon">{icon}</div>
      <h3 className="h6">{title}</h3>
      {message && <p className="text-muted small mb-3">{message}</p>}
      {actionLabel && actionTo && (
        <Link to={actionTo} className="btn btn-forest btn-sm">
          {actionLabel}
        </Link>
      )}
    </div>
  )
}

export default EmptyState