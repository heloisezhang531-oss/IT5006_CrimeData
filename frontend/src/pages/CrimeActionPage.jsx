import { useEffect, useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import ChartCard from '../components/ChartCard'
import {
  fetchCurrentMonthCommunity,
  fetchPredictedRisk,
  fetchRawData,
  fetchTenYearTrend,
  fetchTop10PrimaryType,
} from '../api'

export default function CrimeActionPage() {
  const [communityDist, setCommunityDist] = useState({ month_start: null, data: [] })
  const [riskDist, setRiskDist] = useState({ target_month: null, data: [] })
  const [trend, setTrend] = useState({ data: [] })
  const [topTypes, setTopTypes] = useState({ month_start: null, data: [] })
  const [rawData, setRawData] = useState({ data: [] })

  useEffect(() => {
    Promise.all([
      fetchCurrentMonthCommunity(),
      fetchPredictedRisk(),
      fetchTenYearTrend(),
      fetchTop10PrimaryType(),
      fetchRawData(200),
    ]).then(([a, b, c, d, e]) => {
      setCommunityDist(a)
      setRiskDist(b)
      setTrend(c)
      setTopTypes(d)
      setRawData(e)
    })
  }, [])

  const topCommunity = useMemo(() => communityDist.data.slice(0, 20), [communityDist])
  const topRisk = useMemo(() => riskDist.data.slice(0, 20), [riskDist])

  return (
    <div className="page">
      <h2>Crime Action</h2>
      <p className="subtitle">Current situation + next-month risk + historical trend + raw TiDB data.</p>

      <div className="chart-grid">
        <ChartCard
          title="Current Month Crime Count by Community"
          subtitle={communityDist.month_start ? `Month: ${communityDist.month_start}` : ''}
        >
          <Plot
            data={[
              {
                type: 'bar',
                x: topCommunity.map((d) => d.community_area),
                y: topCommunity.map((d) => d.crime_count),
                marker: { color: '#2563eb' },
              },
            ]}
            layout={{ margin: { l: 40, r: 10, t: 10, b: 40 }, xaxis: { title: 'Community Area' }, yaxis: { title: 'Crime Count' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>

        <ChartCard
          title="Predicted High-Risk Distribution (Next Month)"
          subtitle={riskDist.target_month ? `Target Month: ${riskDist.target_month}` : ''}
        >
          <Plot
            data={[
              {
                type: 'bar',
                x: topRisk.map((d) => d.community_area),
                y: topRisk.map((d) => d.pred_prob),
                marker: { color: '#dc2626' },
              },
            ]}
            layout={{ margin: { l: 40, r: 10, t: 10, b: 40 }, xaxis: { title: 'Community Area' }, yaxis: { title: 'Predicted Risk Probability' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>

        <ChartCard title="10-Year Crime Count Trend (Monthly)">
          <Plot
            data={[
              {
                type: 'scatter',
                mode: 'lines',
                x: trend.data.map((d) => d.month),
                y: trend.data.map((d) => d.crime_count),
                line: { color: '#0f766e', width: 2 },
              },
            ]}
            layout={{ margin: { l: 40, r: 10, t: 10, b: 40 }, xaxis: { title: 'Month' }, yaxis: { title: 'Crime Count' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>

        <ChartCard
          title="Top 10 Primary Type (Current Month)"
          subtitle={topTypes.month_start ? `Month: ${topTypes.month_start}` : ''}
        >
          <Plot
            data={[
              {
                type: 'bar',
                orientation: 'h',
                x: topTypes.data.map((d) => d.crime_count).reverse(),
                y: topTypes.data.map((d) => d.primary_type).reverse(),
                marker: { color: '#7c3aed' },
              },
            ]}
            layout={{ margin: { l: 130, r: 10, t: 10, b: 40 }, xaxis: { title: 'Crime Count' }, yaxis: { title: 'Primary Type' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>
      </div>

      <section className="card raw-table-card">
        <div className="card-header">
          <h3>Raw Data Table (from TiDB)</h3>
          <p>Table: chicago_processed_data (latest 200 records)</p>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>community_area</th>
                <th>month</th>
                <th>count_t1</th>
                <th>arrest_rate</th>
                <th>hardship_index</th>
                <th>spatial_lag_crime_lag1</th>
              </tr>
            </thead>
            <tbody>
              {rawData.data.map((row) => (
                <tr key={`${row.community_area}-${row.month}`}>
                  <td>{row.community_area}</td>
                  <td>{row.month}</td>
                  <td>{row.count_t1}</td>
                  <td>{row.arrest_rate}</td>
                  <td>{row.hardship_index}</td>
                  <td>{row.spatial_lag_crime_lag1}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
