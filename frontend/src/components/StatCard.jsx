function StatCard({ label, value, icon, accent }) {
  return (
    <div className="sc-stat-card">
      {icon && <div className="sc-feature-icon mb-1">{icon}</div>}
      <div className={`sc-stat-value${accent === 'gold' ? ' accent-gold' : ''}`}>{value}</div>
      <div className="sc-stat-label">{label}</div>
    </div>
  )
}

export default StatCard