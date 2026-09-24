function FeatureCard({ icon, title, description }) {
  return (
    <div className="sc-feature-card">
      <div className="sc-feature-icon">{icon}</div>
      <h3 className="h6 mb-2">{title}</h3>
      <p className="text-muted small mb-0">{description}</p>
    </div>
  )
}

export default FeatureCard