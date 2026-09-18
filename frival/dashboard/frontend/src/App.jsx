import React, { useEffect, useState } from 'react'

// ── data helpers ────────────────────────────────────────────────────────────────
const fmtUSD = (v) => (v == null ? '—' : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
const fmtPct = (v) => (v == null ? '—' : `${(Number(v) * 100).toFixed(2)}%`)
const symClass = (v) => (v > 0 ? 'pos' : v < 0 ? 'neg' : '')
const sign = (v) => (v > 0 ? '+' : '')
const ENGINES = ['gold', 'fx_scheduler']

function useBook() {
  const [book, setBook] = useState(null)
  const [err, setErr] = useState(null)
  const refresh = () =>
    fetch('/api/book')
      .then((r) => r.json())
      .then((d) => (d.error ? setErr(d.error) : (setBook(d), setErr(null))))
      .catch((e) => setErr(String(e)))
  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 60_000)
    return () => clearInterval(t)
  }, [])
  return { book, err, refresh }
}

export default function App() {
  const { book, err } = useBook()
  const account = book?.mt5?.account
  const exposure = book?.exposure ?? {}
  const currency = exposure.currency_exposure ?? {}
  const goldState = book?.gold_state
  return (
    <div>
      <header>
        <h1>Frival Book Dashboard</h1>
        <div className="meta">
          {book ? <span>Updated {book.ts ? new Date(book.ts).toLocaleTimeString() : ''}</span> : null}
          {err ? <span style={{ color: 'var(--red)', marginLeft: 12 }}>⚠ {err}</span> : null}
        </div>
      </header>

      <div className="grid">
        {/* ── BOOK OVERVIEW ─────────────────────────────────────────────── */}
        <section className="panel">
          <h2>Book Overview</h2>
          {account ? (
            <>
              <div className="row"><span className="k">Account</span><span><span className={account.server.includes('Demo') ? 'tag demo' : 'tag live'}>{account.server.includes('Demo') ? 'DEMO' : 'LIVE'}</span> {account.login}</span></div>
              <div className="row"><span className="k">Balance</span><span>{fmtUSD(account.balance)}</span></div>
              <div className="row"><span className="k">Equity</span><span>{fmtUSD(account.equity)}</span></div>
              <div className="row"><span className="k">Free margin</span><span>{fmtUSD(account.margin_free)}</span></div>
              <div className="row"><span className="k">Leverage</span><span>1:{account.leverage}</span></div>
              <div className="row"><span className="k">Today PnL (MT5)</span><span className={symClass(book?.combined_today_pnl)}><>{sign(book?.combined_today_pnl)}{fmtUSD(book?.combined_today_pnl)}</></span></div>
              <div className="row"><span className="k">Gross exposure</span><span>{exposure.gross_exposure}</span></div>
              <div className="row"><span className="k">Open positions</span><span>{(book?.mt5?.positions ?? []).length}</span></div>
            </>
          ) : (
            <div className="empty">MT5 unavailable — engine terminal may be down.</div>
          )}
        </section>

        {/* ── CURRENCY FACTOR EXPOSURE ──────────────────────────────────── */}
        <section className="panel">
          <h2>Currency Factor Exposure (the book lens)</h2>
          {Object.keys(currency).length === 0 ? (
            <div className="empty">No open positions — flat book.</div>
          ) : (
            Object.entries(currency).map(([cur, val]) => {
              const mx = Math.max(...Object.values(currency).map(Math.abs), 0.01)
              const pct = (Math.abs(val) / mx) * 100
              const color = val >= 0 ? 'var(--green)' : 'var(--red)'
              return (
                <div key={cur} className="bar-row">
                  <span className="label">{cur}</span>
                  <div className="bar-track" style={{ flex: 1 }}>
                    <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
                  </div>
                  <span className={symClass(val)}>{val.toFixed(3)}</span>
                </div>
              )
            })
          )}
          {exposure.usd_exposure_units != null && exposure.usd_exposure_units !== 0 && (
            <div style={{ marginTop: 10, color: 'var(--muted)', fontSize: 12 }}>
              Net USD exposure: <strong className={symClass(exposure.usd_exposure_units)}>{exposure.usd_exposure_units.toFixed(3)}</strong>
              {' — '}
              {exposure.usd_exposure_units > 0 ? 'book is net LONG the dollar' : 'book is net SHORT the dollar'}
            </div>
          )}
        </section>

        {/* ── GOLD ENGINE ───────────────────────────────────────────────── */}
        <section className="panel">
          <h2>Gold Engine (Rules A/B + C)</h2>
          {goldState ? (
            <div className="micro">
              <div className="row"><span className="k">State</span><span><span className="tag live">{goldState.state}</span></span></div>
              <div className="row"><span className="k">H1 Bias</span><span>{goldState.h1_bias}</span></div>
              <div className="row"><span className="k">Direction</span><span>{goldState.direction ?? '—'}</span></div>
              <div className="row"><span className="k">Watched level</span><span>{goldState.watched_level ? `${goldState.watched_level.kind} @ ${goldState.watched_level.price}` : '—'}</span></div>
              <div className="row"><span className="k">Active trade</span><span>{goldState.active_trade?.ticket ? `#${goldState.active_trade.ticket}` : 'none'}</span></div>
              <div className="row"><span className="k">Today PnL</span><span className={symClass(book?.gold_pnl)}><>{sign(book?.gold_pnl)}{fmtUSD(book?.gold_pnl)}</></span></div>
              <div className="row"><span className="k">Last action</span><span className="empty">{goldState.last_action} — {goldState.last_reason}</span></div>
            </div>
          ) : (
            <div className="empty">No gold engine state file.</div>
          )}
        </section>

        {/* ── ENGINE HEALTH + OPEN POSITIONS ─────────────────────────────── */}
        <section className="panel">
          <h2>Engine Health</h2>
          {book ? (
            ENGINES.map((e) => {
              const h = book.health?.[e]
              return (
                <div key={e} className="row">
                  <span className="k">{e}</span>
                  <span className={h?.alive ? 'pulse' : 'pulse off'}>{h?.alive ? 'ALIVE' : 'OFFLINE'}</span>
                </div>
              )
            })
          ) : (
            <div className="empty">Loading…</div>
          )}
        </section>
      </div>

      {/* ── OPEN POSITIONS TABLE ───────────────────────────────────────── */}
      <div className="grid" style={{ paddingTop: 0 }}>
        <section className="panel" style={{ gridColumn: '1 / -1' }}>
          <h2>Open Positions</h2>
          {(book?.mt5?.positions ?? []).length === 0 ? (
            <div className="empty">None.</div>
          ) : (
            <table>
              <thead>
                <tr><th>Symbol</th><th>Side</th><th>Vol</th><th>Open</th><th>Now</th><th>SL</th><th>TP</th><th>Profit</th><th>Source</th></tr>
              </thead>
              <tbody>
                {(book?.mt5?.positions ?? []).map((p) => (
                  <tr key={p.ticket}>
                    <td>{p.symbol}</td>
                    <td>{p.type}</td>
                    <td>{p.volume}</td>
                    <td>{p.price_open}</td>
                    <td>{p.price_current}</td>
                    <td>{p.sl || '—'}</td>
                    <td>{p.tp || '—'}</td>
                    <td className={symClass(p.profit)}>{sign(p.profit)}{fmtUSD(p.profit)}</td>
                    <td className="empty">{p.comment || 'manual?'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  )
}