function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="sc-footer">
      <div className="container d-flex flex-column flex-md-row justify-content-between align-items-center gap-2">
        <div>
          <strong className="text-white">SmartCart AI</strong>
          <span className="ms-2 small">Grocery price comparison, built for savings.</span>
        </div>
        <div className="small">
          &copy; {year} SmartCart AI &middot; Final-year project &middot; Demo data
        </div>
      </div>
    </footer>
  )
}

export default Footer