import { Link } from 'react-router-dom'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <Link to="/" className="footer__logo">MediOrbit</Link>
          <p className="footer__tagline">Tamil Nadu's medical tourism platform — AI-ranked, transparently priced.</p>
        </div>
        <div className="footer__links">
          <div className="footer__col">
            <span className="footer__col-heading">Platform</span>
            <Link to="/results" className="footer__link">Find hospitals</Link>
            <a href="#how" className="footer__link">How it works</a>
          </div>
          <div className="footer__col">
            <span className="footer__col-heading">Specialties</span>
            <a href="#" className="footer__link">Orthopaedics</a>
            <a href="#" className="footer__link">Cardiac Surgery</a>
            <a href="#" className="footer__link">Neurology</a>
          </div>
          <div className="footer__col">
            <span className="footer__col-heading">Contact</span>
            <a href="mailto:hello@medioorbit.com" className="footer__link">hello@medioorbit.com</a>
          </div>
        </div>
      </div>
      <div className="footer__bottom">
        <span>© {new Date().getFullYear()} MediOrbit. All rights reserved.</span>
      </div>
    </footer>
  )
}
