import { useEffect, useState } from 'react'
import { Binary, Boxes, Coins, Search, Sparkles } from 'lucide-react'
import { algorithmsService } from '../services/algorithms'
import { getErrorMessage } from '../services/api'
import { formatPrice } from '../services/products'

function Names({ items, price }) {
  return <ol className="algorithm-list">{items.map(item => <li key={item.id}>{item.name}{price && <span>{formatPrice(item[price])}</span>}</li>)}</ol>
}

export default function AlgorithmsPage() {
  const [budget, setBudget] = useState('100000')
  const [change, setChange] = useState('0')
  const [search, setSearch] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load(event) {
    event?.preventDefault()
    setLoading(true)
    setError('')
    try {
      setData(await algorithmsService.overview({ budget, change, search }))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to run the algorithm demonstration.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return <main className="page algorithms-page">
    <header className="page-heading"><div><p className="eyebrow">Academic integration</p><h1>Algorithms</h1><p className="page-subtitle">Seven explicit algorithms applied to current catalog and payment data.</p></div></header>
    <form className="algorithm-controls" onSubmit={load}>
      <label>Restocking budget (COP)<input type="number" min="1000" max="2000000" step="1000" value={budget} onChange={event => setBudget(event.target.value)} /></label>
      <label>Change to suggest (COP)<input type="number" min="0" max="2000000" step="50" value={change} onChange={event => setChange(event.target.value)} /></label>
      <label>Exact product name<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search with binary search" /></label>
      <button type="submit" className="primary-button" disabled={loading}>{loading ? 'Running...' : 'Run algorithms'}</button>
    </form>
    {error && <p role="alert" className="error-banner">{error}</p>}
    {!loading && data && <>
      <section className="algorithm-section"><div className="section-heading"><h2><Boxes size={17} /> Sorting algorithms</h2><span className="count-badge">{data.catalog_size}</span></div><p className="table-note">Each implementation receives the same live product snapshot. Database ordering remains in use for transactional screens.</p>
        <div className="algorithm-columns">
          <article><h3>Bubble Sort</h3><p>Alphabetical name order · O(n²)</p><Names items={data.sorting.bubble} /></article>
          <article><h3>Insertion Sort</h3><p>Purchase price order · O(n²)</p><Names items={data.sorting.insertion} price="purchase_price" /></article>
          <article><h3>Quick Sort</h3><p>Sale price order · O(n log n) average</p><Names items={data.sorting.quick} price="sale_price" /></article>
        </div>
      </section>
      <section className="algorithm-columns algorithm-section">
        <article><h3><Search size={17} /> Binary search</h3><p>Searches the Bubble Sort output by exact product name.</p>{search ? (data.binary_search.found ? <p className="algorithm-result">Found: <strong>{data.binary_search.found.name}</strong></p> : <p className="algorithm-result">No exact match found.</p>) : <p className="algorithm-result">Enter a product name to run the search.</p>}</article>
        <article><h3><Coins size={17} /> Greedy change</h3><p>Uses the largest Colombian denomination that fits at each step.</p><p className="algorithm-result">{data.greedy_change.breakdown.length ? data.greedy_change.breakdown.map(item => `${item.count} × ${formatPrice(item.denomination)}`).join(', ') : 'No change required.'}</p></article>
        <article><h3><Sparkles size={17} /> Lexicographic greedy</h3><p>Builds the largest string by placing each character at either end.</p><p className="algorithm-result">{search ? data.lexicographic_greedy.result : 'Enter text in the product field.'}</p></article>
      </section>
      <section className="algorithm-section"><div className="section-heading"><h2><Binary size={17} /> 0/1 Knapsack</h2></div><p className="table-note">Selects at most one unit of each active product to maximize estimated margin within the entered restocking budget. Costs use COP 1,000 blocks, rounded up so the recommendation does not exceed the actual budget.</p><div className="algorithm-summary"><span>Budget <strong>{formatPrice(data.knapsack.budget)}</strong></span><span>Selected cost <strong>{formatPrice(data.knapsack.total_cost)}</strong></span><span>Estimated margin <strong>{formatPrice(data.knapsack.total_benefit)}</strong></span></div><Names items={data.knapsack.selected} price="purchase_price" /></section>
    </>}
  </main>
}
