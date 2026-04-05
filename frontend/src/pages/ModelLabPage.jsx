import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import ChartCard from '../components/ChartCard'
import { fetchFeatureImportance, fetchModelMetrics } from '../api'

export default function ModelLabPage() {
  const [metrics, setMetrics] = useState({ data: [] })
  const [importance, setImportance] = useState({ data: [] })

  useEffect(() => {
    Promise.all([fetchModelMetrics(), fetchFeatureImportance()]).then(([a, b]) => {
      setMetrics(a)
      setImportance(b)
    })
  }, [])

  return (
    <div className="page">
      <h2>Model Lab</h2>
      <p className="subtitle">Model predictive capability and feature importance.</p>

      <div className="chart-grid single-col">
        <ChartCard title="Model Predictive Metrics (with hardship features)">
          <Plot
            data={[
              {
                type: 'bar',
                x: metrics.data.map((d) => d.model),
                y: metrics.data.map((d) => d.test_roc_auc),
                name: 'Test ROC-AUC',
                marker: { color: '#16a34a' },
              },
              {
                type: 'bar',
                x: metrics.data.map((d) => d.model),
                y: metrics.data.map((d) => d.test_pr_auc),
                name: 'Test PR-AUC',
                marker: { color: '#0284c7' },
              },
              {
                type: 'bar',
                x: metrics.data.map((d) => d.model),
                y: metrics.data.map((d) => d.test_f1),
                name: 'Test F1',
                marker: { color: '#f59e0b' },
              },
            ]}
            layout={{ barmode: 'group', margin: { l: 40, r: 10, t: 10, b: 40 }, yaxis: { title: 'Score' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>

        <ChartCard title="Feature Importance (Global SHAP)">
          <Plot
            data={[
              {
                type: 'bar',
                orientation: 'h',
                x: importance.data.map((d) => d.mean_abs_shap).reverse(),
                y: importance.data.map((d) => d.feature).reverse(),
                marker: { color: '#9333ea' },
              },
            ]}
            layout={{ margin: { l: 180, r: 10, t: 10, b: 40 }, xaxis: { title: 'Mean |SHAP|' } }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </ChartCard>
      </div>
    </div>
  )
}
