import { NavLink, Route, Routes } from 'react-router-dom'
import CrimeActionPage from './pages/CrimeActionPage'
import ModelLabPage from './pages/ModelLabPage'

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Chicago Predictive Policing Dashboard</h1>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Crime Action
          </NavLink>
          <NavLink to="/model-lab" className={({ isActive }) => (isActive ? 'active' : '')}>
            Model Lab
          </NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<CrimeActionPage />} />
          <Route path="/model-lab" element={<ModelLabPage />} />
        </Routes>
      </main>
    </div>
  )
}
