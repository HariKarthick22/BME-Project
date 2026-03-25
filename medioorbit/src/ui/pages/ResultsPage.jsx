import { useState, useEffect } from 'react';
import HospitalCard from '../components/HospitalCard';
import { HospitalFilters } from '../components/HospitalFilters';
import { hospitalService } from '../../services/hospitalService';
import {
  normalizeHospitals,
  getTopHospitals,
  filterHospitals,
  sortHospitals
} from '../../utils/normalizeData';
import '../styles/ResultsPage.css';

/**
 * Results Page
 * Displays top 5 hospitals from chat results or API
 * Supports filtering, sorting, and detailed views
 */
export default function ResultsPage() {
  const [allHospitals, setAllHospitals] = useState([]);
  const [displayHospitals, setDisplayHospitals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedHospital, setSelectedHospital] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  const [filters, setFilters] = useState({
    specialty: '',
    city: '',
    minRating: 0,
    maxPrice: 999999999,
    sortBy: 'score'
  });

  /**
   * Load hospitals on component mount
   */
  useEffect(() => {
    loadHospitals();
  }, []);

  /**
   * Apply filters whenever filter state changes
   */
  useEffect(() => {
    applyFilters();
  }, [filters, allHospitals]);

  /**
   * Load hospitals from cache or API
   */
  const loadHospitals = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get top 5 from search results (with fallback to API)
      const hospitals = await hospitalService.getSearchResults(true);

      if (!hospitals || hospitals.length === 0) {
        setError('No hospitals available');
        setLoading(false);
        return;
      }

      // Normalize hospital data
      const normalized = normalizeHospitals(hospitals);

      // Get top 5 by AI score
      const top5 = getTopHospitals(normalized, 5);

      setAllHospitals(top5);
      setDisplayHospitals(top5);
    } catch (err) {
      console.error('Error loading hospitals:', err);
      setError(err.message || 'Failed to load hospitals');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Apply filters and sorting to hospitals
   */
  const applyFilters = () => {
    if (allHospitals.length === 0) return;

    // Apply filters
    let filtered = filterHospitals(allHospitals, {
      specialty: filters.specialty,
      city: filters.city,
      minRating: filters.minRating,
      maxPrice: filters.maxPrice
    });

    // Apply sorting
    const sorted = sortHospitals(filtered, filters.sortBy, false);

    setDisplayHospitals(sorted);
  };

  /**
   * Update single filter
   */
  const updateFilter = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  /**
   * Handle hospital card click
   */
  const handleHospitalSelect = (hospital) => {
    setSelectedHospital(hospital);
    setShowDetail(true);
  };

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setFilters({
      specialty: '',
      city: '',
      minRating: 0,
      maxPrice: 999999999,
      sortBy: 'score'
    });
  };

  /**
   * Refresh hospital list
   */
  const handleRefresh = () => {
    loadHospitals();
  };

  if (loading) {
    return (
      <div className="results-page loading">
        <div className="spinner"></div>
        <p>Loading hospitals...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-page error">
        <div className="error-container">
          <h2>⚠️ {error}</h2>
          <button onClick={handleRefresh} className="btn-retry">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="results-page">
      <div className="results-header">
        <div className="header-content">
          <h1>🏥 Top {allHospitals.length} Hospitals for Your Needs</h1>
          <p className="result-count">
            Found <strong>{displayHospitals.length}</strong> hospitals
            {displayHospitals.length < allHospitals.length && ` (filtered from ${allHospitals.length})`}
          </p>
        </div>
        <button onClick={handleRefresh} className="btn-refresh" title="Refresh">
          🔄
        </button>
      </div>

      <div className="results-container">
        {/* Filters Sidebar */}
        <aside className="filters-sidebar">
          <HospitalFilters
            filters={filters}
            onFilterChange={updateFilter}
            onClearFilters={clearFilters}
          />
        </aside>

        {/* Hospital Cards Grid */}
        <main className="hospitals-grid">
          {displayHospitals.length > 0 ? (
            <>
              <div className="cards-container">
                {displayHospitals.map((hospital, idx) => (
                  <div
                    key={hospital.id}
                    className="hospital-card-wrapper"
                    onClick={() => handleHospitalSelect(hospital)}
                  >
                    <div className="rank-badge">#{idx + 1}</div>
                    <HospitalCard hospital={hospital} />
                  </div>
                ))}
              </div>

              {/* Summary Stats */}
              <div className="results-summary">
                <div className="stat-box">
                  <span className="stat-label">Avg Rating</span>
                  <span className="stat-value">
                    {displayHospitals.length > 0
                      ? (
                          displayHospitals.reduce((sum, h) => sum + (h.rating || 0), 0) /
                          displayHospitals.length
                        ).toFixed(1)
                      : '0.0'}
                    ⭐
                  </span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Avg Price</span>
                  <span className="stat-value">
                    ₹
                    {displayHospitals.length > 0
                      ? Math.round(
                          displayHospitals.reduce((sum, h) => sum + (h.pricing?.total || 0), 0) /
                            displayHospitals.length
                        ).toLocaleString('en-IN')
                      : '0'}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="no-results">
              <p>No hospitals match your filters</p>
              <button onClick={clearFilters} className="btn-clear">
                Clear All Filters
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Detail View Modal */}
      {showDetail && selectedHospital && (
        <HospitalDetailModal
          hospital={selectedHospital}
          onClose={() => setShowDetail(false)}
        />
      )}
    </div>
  );
}

/**
 * Hospital Detail Modal Component
 */
function HospitalDetailModal({ hospital, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <div className="modal-body">
          <h2>{hospital.name}</h2>
          <p className="hospital-location">📍 {hospital.location}</p>

          {hospital.heroImage && (
            <img src={hospital.heroImage} alt={hospital.name} className="modal-image" />
          )}

          <div className="detail-section">
            <h3>📊 Statistics</h3>
            <div className="stats-grid">
              <div className="stat">
                <span className="number">{hospital.aiScore}</span>
                <span className="label">AI Score</span>
              </div>
              <div className="stat">
                <span className="number">{hospital.successRate}%</span>
                <span className="label">Success Rate</span>
              </div>
              <div className="stat">
                <span className="number">₹{hospital.pricing?.total?.toLocaleString('en-IN')}</span>
                <span className="label">Avg Cost</span>
              </div>
            </div>
          </div>

          <div className="detail-section">
            <h3>🔬 Specialties</h3>
            <div className="chips">
              {hospital.specialties?.map((spec, idx) => (
                <span key={idx} className="chip">{spec}</span>
              ))}
            </div>
          </div>

          {Array.isArray(hospital.procedures) && hospital.procedures.length > 0 && (
            <div className="detail-section">
              <h3>🏥 Procedures</h3>
              <div className="chips">
                {hospital.procedures.map((proc, idx) => (
                  <span key={idx} className="chip">{proc}</span>
                ))}
              </div>
            </div>
          )}

          <div className="detail-section">
            <h3>💳 Pricing Range</h3>
            <div className="price-range">
              <div className="price-item">
                <span>Min:</span>
                <span className="price">₹{hospital.pricing?.min?.toLocaleString('en-IN')}</span>
              </div>
              <div className="price-item">
                <span>Max:</span>
                <span className="price">₹{hospital.pricing?.max?.toLocaleString('en-IN')}</span>
              </div>
            </div>
          </div>

          {hospital.phone && (
            <div className="detail-section">
              <h3>📞 Contact</h3>
              <p>{hospital.phone}</p>
              {hospital.email && <p>{hospital.email}</p>}
            </div>
          )}

          <button
            className="btn-contact"
            onClick={() => {
              if (hospital.googleMapsUrl && hospital.googleMapsUrl !== '#') {
                window.open(hospital.googleMapsUrl, '_blank');
              }
            }}
            disabled={!hospital.googleMapsUrl || hospital.googleMapsUrl === '#'}
            title={hospital.googleMapsUrl && hospital.googleMapsUrl !== '#' ? 'Open directions in new tab' : 'Directions link unavailable'}
          >
            Get Directions 🗺️
          </button>
        </div>
      </div>
    </div>
  );
}
