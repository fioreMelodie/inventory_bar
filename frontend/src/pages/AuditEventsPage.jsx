import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Eye, RotateCcw, Search, X } from 'lucide-react'
import { auditService } from '../services/audit'
import { venuesService } from '../services/venues'
import { getErrorMessage } from '../services/api'

const fields = ['start_date', 'end_date', 'username', 'event_type', 'venue']
const venueLabel = event => event.venue_recorded ? event.venue_name || 'Not associated' : 'Not recorded'
const eventDate = value => new Date(value).toLocaleString('en-US', {
  timeZone: 'America/Bogota', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit',
  minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, timeZoneName: 'short',
})

function AuditEventDialog({ id, onClose }) {
  const dialog = useRef(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)
  useEffect(() => { dialog.current?.showModal() }, [])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setData(null)
    setError('')
    auditService.detail(id).then(result => { if (!cancelled) setData(result) })
      .catch(err => { if (!cancelled) setError(getErrorMessage(err, 'Unable to load event details.')) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, refresh])
  return <dialog ref={dialog} className="audit-dialog" aria-labelledby="audit-event-title" onClose={onClose}>
    <header><div><p className="eyebrow">Event #{id}</p><h2 id="audit-event-title">Event details</h2></div>
      <button className="icon-button" aria-label="Close event details" title="Close event details" onClick={() => dialog.current?.close()}><X size={20} /></button></header>
    {loading && <p className="empty-cell">Loading event...</p>}
    {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => setRefresh(value => value + 1)}>Retry</button></div>}
    {data && <>
      <dl className="receipt-metadata">
        <div><dt>Username</dt><dd>{data.username || 'Not recorded'}</dd></div>
        <div><dt>Event type</dt><dd>{data.event_type_label}<span className="sales-secondary">{data.event_type}</span></dd></div>
        <div><dt>Entity</dt><dd>{data.entity || 'Not associated'}{data.entity_id && ' #' + data.entity_id}</dd></div>
        <div><dt>Venue</dt><dd>{venueLabel(data)}</dd></div>
        <div><dt>Date / Time (Bogota)</dt><dd><time dateTime={data.created_at}>{eventDate(data.created_at)}</time></dd></div>
        <div><dt>IP address</dt><dd>{data.ip_address || 'Not recorded'}</dd></div>
        <div className="audit-timestamp"><dt>Recorded timestamp</dt><dd>{data.created_at}</dd></div>
      </dl>
      <section className="audit-description" aria-label="Event description"><h3>Description</h3><p>{data.description || 'No description recorded.'}</p></section>
    </>}
  </dialog>
}

export default function AuditEventsPage() {
  const [params, setParams] = useSearchParams()
  const query = params.toString()
  const applied = Object.fromEntries(fields.filter(key => params.get(key)).map(key => [key, params.get(key)]))
  const rawPage = Number(params.get('page') || 1)
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1
  const [draft, setDraft] = useState(applied)
  const [venues, setVenues] = useState([])
  const [data, setData] = useState(null)
  const [eventTypes, setEventTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [venueError, setVenueError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [selected, setSelected] = useState(null)
  useEffect(() => { setDraft(applied) }, [query])
  useEffect(() => {
    let cancelled = false
    venuesService.list({ includeInactive: true }).then(list => {
      if (!cancelled) { setVenues(list); setVenueError('') }
    }).catch(err => { if (!cancelled) setVenueError(getErrorMessage(err, 'Unable to load venues.')) })
    return () => { cancelled = true }
  }, [refresh])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setData(null)
    setError('')
    auditService.list({ ...applied, page }).then(result => {
      if (!cancelled) { setData(result); setEventTypes(result.event_types) }
    }).catch(err => {
      if (!cancelled) {
        const values = err?.response?.data
        const fieldError = fields.map(key => values?.[key]?.[0]).find(Boolean)
        setError(fieldError || getErrorMessage(err, 'Unable to load events.'))
      }
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [query, refresh])

  function submit(event) {
    event.preventDefault()
    if (draft.start_date && draft.end_date && draft.start_date > draft.end_date) {
      setError('End date must be on or after start date.')
      return
    }
    setParams(Object.fromEntries(fields.filter(key => draft[key]?.trim()).map(key => [key, draft[key].trim()])))
    setRefresh(value => value + 1)
  }

  return <main className="audit-page">
    <header className="page-heading"><div><p className="eyebrow">Audit</p><h1>Event log</h1><p className="page-subtitle">Cafe Colombia Bar</p></div></header>
    <form className="sales-filters" aria-label="Audit filters" onSubmit={submit}>
      <div><label htmlFor="audit-start">From date</label><input id="audit-start" type="date" value={draft.start_date || ''} onChange={event => setDraft({ ...draft, start_date: event.target.value })} /></div>
      <div><label htmlFor="audit-end">Through date</label><input id="audit-end" type="date" value={draft.end_date || ''} onChange={event => setDraft({ ...draft, end_date: event.target.value })} /></div>
      <div><label htmlFor="audit-username">Username</label><input id="audit-username" type="search" maxLength={150} value={draft.username || ''} onChange={event => setDraft({ ...draft, username: event.target.value })} /></div>
      <div><label htmlFor="audit-type">Event type</label><select id="audit-type" value={draft.event_type || ''} onChange={event => setDraft({ ...draft, event_type: event.target.value })}><option value="">All event types</option>{eventTypes.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}</select></div>
      <div><label htmlFor="audit-venue">Venue</label><select id="audit-venue" value={draft.venue || ''} onChange={event => setDraft({ ...draft, venue: event.target.value })}><option value="">All venues</option>{venues.map(venue => <option key={venue.id} value={venue.id}>{venue.name}</option>)}<option value="__none__">Not associated</option><option value="__unrecorded__">Not recorded</option></select></div>
      <div className="receipt-filter-actions"><button className="primary-button" type="submit" disabled={loading}><Search size={16} /> Search events</button><button className="icon-button refresh-button" type="button" aria-label="Clear filters" title="Clear filters" disabled={loading} onClick={() => { setParams({}); setDraft({}); setRefresh(value => value + 1) }}><RotateCcw size={18} /></button></div>
    </form>
    {(error || venueError) && <div className="error-banner" role="alert"><span>{error || venueError}</span><button onClick={() => setRefresh(value => value + 1)} disabled={loading}>Retry</button></div>}
    <section aria-label="Audit events" aria-busy={loading}>
      {loading && <p className="empty-cell">Loading events...</p>}
      {data && (data.count ? <div className="data-table-wrap"><table className="audit-table">
        <thead><tr><th>Date / Time (Bogota)</th><th>Username</th><th>Event type</th><th>Entity</th><th>Venue</th><th><span className="sr-only">Event details</span></th></tr></thead>
        <tbody>{data.results.map(event => <tr key={event.id}>
          <td><time dateTime={event.created_at}>{eventDate(event.created_at)}</time></td>
          <td data-label="Username">{event.username || 'Not recorded'}</td><td data-label="Event type">{event.event_type_label}</td>
          <td data-label="Entity">{event.entity || 'Not associated'}{event.entity_id && ' #' + event.entity_id}</td><td data-label="Venue">{venueLabel(event)}</td>
          <td><button className="icon-button" title={'View event ' + event.id} aria-label={'View event ' + event.id} onClick={() => setSelected(event.id)}><Eye size={18} /></button></td>
        </tr>)}</tbody>
      </table></div> : <div className="empty-state"><strong>No events found for the selected filters.</strong></div>)}
    </section>
    {data && <footer className="receipts-pagination"><p className="table-note" aria-live="polite">{data.count} events · Page {page}</p><div>
      <button className="icon-button" title="Previous page" aria-label="Previous page" disabled={!data.previous || loading} onClick={() => setParams({ ...applied, page: String(page - 1) })}><ChevronLeft size={18} /></button>
      <button className="icon-button" title="Next page" aria-label="Next page" disabled={!data.next || loading} onClick={() => setParams({ ...applied, page: String(page + 1) })}><ChevronRight size={18} /></button></div></footer>}
    {selected !== null && <AuditEventDialog id={selected} onClose={() => setSelected(null)} />}
  </main>
}
