import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import HospitalCard from '../components/HospitalCard'
import { hospitals, platformStats, specialties } from '../../data/hospitals'
import '../styles/HomePage.css'

const CHAT_STEPS = [
  'Scanning hospital database...',
  'Verifying accreditations & success rates...',
  'Comparing cost against market average...',
  'Ranking by AI compatibility score...',
  'Preparing your personalised matches...',
]

const CHIPS = [
  'Knee replacement under ₹5L in Coimbatore',
  'Heart bypass surgery with JCI accreditation',
  'Brain surgery — best success rate Tamil Nadu',
  'Kidney transplant under ₹10L',
]

function AIChat() {
  const [query, setQuery] = useState('')
  const [phase, setPhase] = useState('idle')
  const [completedSteps, setCompletedSteps] = useState([])
  const [currentStep, setCurrentStep] = useState(-1)
  const navigate = useNavigate()

  const startSearch = (q) => {
    if (!q.trim()) return
    setQuery(q)
    setPhase('searching')
    setCompletedSteps([])
    setCurrentStep(0)
  }

  useEffect(() => {
    if (phase !== 'searching') return
    if (currentStep >= CHAT_STEPS.length) {
      setPhase('done')
      return
    }
    const timer = setTimeout(() => {
      setCompletedSteps(prev => [...prev, currentStep])
      setCurrentStep(prev => prev + 1)
    }, 480)
    return () => clearTimeout(timer)
  }, [phase, currentStep])

  const reset = () => {
    setPhase('idle')
    setQuery('')
    setCompletedSteps([])
    setCurrentStep(-1)
  }

  return (
    <div className="ai-chat">
      {phase === 'idle' && (
        <>
          <div className="ai-chat__input-row">
            <input
              className="ai-chat__input"
              placeholder="Describe what you need — procedure, budget, city..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && startSearch(query)}
            />
            <button className="ai-chat__submit" onClick={() => startSearch(query)}>
              Find Hospitals
            </button>
          </div>
          <div className="ai-chat__chips">
            {CHIPS.map(chip => (
              <button key={chip} className="ai-chat__chip" onClick={() => startSearch(chip)}>
                {chip}
              </button>
            ))}
          </div>
        </>
      )}

      {(phase === 'searching' || phase === 'done') && (
        <div className="ai-chat__thinking">
          <p className="ai-chat__query-echo">"{query}"</p>
          <div className="ai-chat__steps">
            {CHAT_STEPS.map((step, i) => {
              const isDone = completedSteps.includes(i)
              const isActive = currentStep === i && phase === 'searching'
              return (
                <div
                  key={i}
                  className={`ai-chat__step${isDone ? ' done' : ''}${isActive ? ' active' : ''}`}
                  style={{ animationDelay: `${i * 0.08}s` }}
                >
                  <span className="ai-chat__step-icon">
                    {isDone ? '✓' : isActive ? '●' : '○'}
                  </span>
                  <span>{step}</span>
                </div>
              )
            })}
          </div>
          {phase === 'done' && (
            <>
              <button
                className="ai-chat__result-btn anim-scale-in"
                onClick={() => navigate('/results', { state: { query } })}
              >
                {hospitals.length} hospitals matched — view results →
              </button>
              <button className="ai-chat__reset" onClick={reset}>Search again</button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function HomePage() {
  return (
    <div className="home">
      <Navbar />

      {/* HERO */}
      <section className="hero">
        <div className="hero__inner">
          <p className="hero__eyebrow anim-fade-up">Tamil Nadu's Medical Tourism Platform</p>
          <h1 className="hero__headline anim-fade-up" style={{ animationDelay: '0.08s' }}>
            Find the right hospital.<br />Not just the nearest one.
          </h1>
          <p className="hero__sub anim-fade-up" style={{ animationDelay: '0.16s' }}>
            Describe your procedure and budget — AI finds, ranks and books the best hospital for you.
          </p>
          <div className="hero__chat anim-fade-up" style={{ animationDelay: '0.24s' }}>
            <AIChat />
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="stats">
        <div className="stats__grid">
          <div className="stats__item">
            <span className="stats__number">{platformStats.hospitalCount}</span>
            <span className="stats__label">Partner hospitals</span>
          </div>
          <div className="stats__item">
            <span className="stats__number">{platformStats.avgSavings}%</span>
            <span className="stats__label">Average cost savings</span>
          </div>
          <div className="stats__item">
            <span className="stats__number">{platformStats.avgMatchTime}s</span>
            <span className="stats__label">Average match time</span>
          </div>
          <div className="stats__item">
            <span className="stats__number">{platformStats.languages}</span>
            <span className="stats__label">Languages supported</span>
          </div>
        </div>
      </section>

      {/* FEATURED HOSPITALS */}
      <section className="featured">
        <div className="section-header">
          <h2 className="section-title">Trusted partners across Tamil Nadu</h2>
          <p className="section-sub">Every hospital is independently scored by our AI across 40+ metrics.</p>
        </div>
        <div className="featured__grid">
          {hospitals.map(h => <HospitalCard key={h.id} hospital={h} />)}
        </div>
      </section>

      {/* SPECIALTIES */}
      <section className="specialties">
        <div className="section-header">
          <h2 className="section-title">Browse by specialty</h2>
        </div>
        <div className="specialties__grid">
          {specialties.map(s => (
            <div key={s.id} className="specialty-card" onClick={() => {}}>
              <span className="specialty-card__label">{s.label}</span>
              <span className="specialty-card__sub">{s.subtitle}</span>
            </div>
          ))}
        </div>
      </section>

      {/* WHY */}
      <section className="why" id="how">
        <div className="why__inner">
          <h2 className="why__title">Why patients choose MediOrbit</h2>
          <div className="why__grid">
            {[
              { n: '01', title: 'AI-ranked, not sponsored', body: 'Every result is sorted by clinical score — success rates, accreditations, and value. No hospital pays to rank higher.' },
              { n: '02', title: 'Transparent pricing', body: 'See the full cost breakdown before you book. No surprises, no hidden fees, no vague estimates.' },
              { n: '03', title: 'End-to-end coordination', body: 'We handle consultation booking, travel logistics, accommodation, and post-procedure follow-up.' },
              { n: '04', title: 'Verified clinical data', body: 'Every success rate and patient review is independently verified. We never publish unconfirmed figures.' },
            ].map(item => (
              <div key={item.n} className="why__item">
                <span className="why__num">{item.n}</span>
                <h3 className="why__item-title">{item.title}</h3>
                <p className="why__item-body">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
