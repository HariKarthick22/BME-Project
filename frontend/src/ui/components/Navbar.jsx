import { Link } from 'react-router-dom'
import './Navbar.css'

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to="/" className="navbar__logo">MediOrbit</Link>
        <nav className="navbar__nav">
          <a href="#how" className="navbar__link">How it works</a>
          <Link to="/results" className="navbar__link">Find hospitals</Link>
          <a href="mailto:hello@medioorbit.com" className="navbar__cta">Get started</a>
        </nav>
      </div>
    </header>
  )
}
