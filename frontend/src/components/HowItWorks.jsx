const steps = [
  {
    title: 'Search for a product',
    description: 'Type a product name, brand, or category to find what you\'re looking for.'
  },
  {
    title: 'Compare across platforms',
    description: 'See the live price on Blinkit, Zepto, Instamart and Flipkart Minutes, side by side.'
  },
  {
    title: 'Buy from the best deal',
    description: 'We highlight the lowest price and how much you save, so the decision is instant.'
  }
]

function HowItWorks() {
  return (
    <section className="py-5">
      <div className="container">
        <h2 className="h4 text-center mb-4">How It Works</h2>
        <div className="row g-4">
          {steps.map((step, index) => (
            <div className="col-md-4" key={step.title}>
              <div className="sc-step">
                <div className="sc-step-number">{index + 1}</div>
                <div>
                  <h3 className="h6 mb-1">{step.title}</h3>
                  <p className="text-muted small mb-0">{step.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks