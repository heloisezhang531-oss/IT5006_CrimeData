export default function ChartCard({ title, subtitle, children }) {
  return (
    <section className="card">
      <div className="card-header">
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      <div className="card-body">{children}</div>
    </section>
  )
}
