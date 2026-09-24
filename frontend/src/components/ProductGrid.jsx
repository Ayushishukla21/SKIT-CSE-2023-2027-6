import ProductCard from './ProductCard'

function ProductGrid({ products }) {
  return (
    <div className="row g-3">
      {products.map((product) => (
        <div className="col-6 col-md-4 col-lg-3" key={product.id}>
          <ProductCard product={product} />
        </div>
      ))}
    </div>
  )
}

export default ProductGrid