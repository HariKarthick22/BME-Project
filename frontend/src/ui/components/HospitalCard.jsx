import { useNavigate } from 'react-router-dom';
import ScoreRing from './ScoreRing';
import './HospitalCard.css';
import { useNavigation } from '../../context/NavigationAgent';

export default function HospitalCard({ hospital }) {
  const navigate = useNavigate();
  const { highlightHospital, clearHighlight } = useNavigation();
  
  // Safe field access with fallbacks
  const totalCost = hospital?.pricing?.total || 0;
  const marketAverage = hospital?.pricing?.marketAverage || totalCost * 1.2;
  const savings = marketAverage > 0 ? Math.round((1 - totalCost / marketAverage) * 100) : 0;
  const aiScore = hospital?.aiScore || 85;
  const successRate = hospital?.stats?.successRate || hospital?.success_rate || 0;
  const specialties = hospital?.specialties || [];
  const name = hospital?.name || 'Hospital';
  const city = hospital?.city || 'Unknown';
  const location = hospital?.location || city;
  const heroImage = hospital?.heroImage || null;
  const googleMapsUrl = hospital?.googleMapsUrl || '#';

  const handleMouseEnter = () => {
    highlightHospital(hospital);
  };

  const handleMouseLeave = () => {
    clearHighlight();
  };

  return (
    <article
      className="hosp-card"
      onClick={() => navigate(`/hospital/${hospital.id}`)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="hosp-card__image">
        {heroImage
          ? <img src={heroImage} alt={name} loading="lazy" />
          : <div className="hosp-card__image-placeholder" />}
        <span className="hosp-card__city-tag">{city}</span>
      </div>
      <div className="hosp-card__body">
        <div className="hosp-card__header">
          <div>
            <h3 className="hosp-card__name">{name}</h3>
            <p className="hosp-card__location">{location}</p>
          </div>
          <ScoreRing score={aiScore} size={56} />
        </div>
        <div className="hosp-card__stats">
          <div className="hosp-card__stat">
            <span className="hosp-card__stat-value">₹{(totalCost/100000).toFixed(1)}L</span>
            <span className="hosp-card__stat-label">Starting price</span>
          </div>
          <div className="hosp-card__stat">
            <span className="hosp-card__stat-value">{successRate}%</span>
            <span className="hosp-card__stat-label">Success rate</span>
          </div>
          <div className="hosp-card__stat">
            <span className="hosp-card__stat-value savings">-{savings}%</span>
            <span className="hosp-card__stat-label">vs market avg</span>
          </div>
        </div>
        <div className="hosp-card__specialties">
          {specialties.slice(0,3).map(s => (
            <span key={s} className="hosp-card__tag">{s}</span>
          ))}
        </div>
        <div className="hosp-card__footer">
          <button className="hosp-card__btn-primary">View Hospital</button>
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hosp-card__maps-link"
            onClick={e => e.stopPropagation()}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            View on Maps
          </a>
        </div>
      </div>
    </article>
  );
}
