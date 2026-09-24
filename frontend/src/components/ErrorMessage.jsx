function ErrorMessage({ message, onRetry }) {
  return (
    <div className="alert alert-danger d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2">
      <span>{message || 'Something went wrong. Please try again.'}</span>
      {onRetry && (
        <button type="button" className="btn btn-outline-danger btn-sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export default ErrorMessage