function LoadingSpinner({ label = 'Loading...' }) {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center py-5">
      <div className="spinner-border sc-spinner" role="status">
        <span className="visually-hidden">{label}</span>
      </div>
      <p className="text-muted mt-2 mb-0">{label}</p>
    </div>
  )
}

export default LoadingSpinner