import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="container py-5">
      <div className="sc-state-box">
        <div className="sc-state-icon">🧭</div>
        <h1 className="h5">Page not found</h1>
        <p className="text-muted small mb-3">The page you're looking for doesn't exist.</p>
        <Link to="/" className="btn btn-forest btn-sm">
          Go home
        </Link>
      </div>
    </div>
  )
}

export default NotFoundPage