/**
 * Data Normalization Utilities
 * Convert backend data formats to frontend-friendly formats
 */

/**
 * Parse JSON string OR return as-is if already array
 * @param {string|Array} field - Field to parse
 * @param {*} defaultValue - Default if parsing fails
 * @returns {Array} Parsed array or default
 */
const parseJsonField = (field, defaultValue = []) => {
  if (Array.isArray(field)) return field;
  if (typeof field === 'string') {
    try {
      const parsed = JSON.parse(field);
      return Array.isArray(parsed) ? parsed : defaultValue;
    } catch {
      return defaultValue;
    }
  }
  return defaultValue;
};

/**
 * Normalize hospital data from backend to frontend format
 * Converts snake_case to camelCase, handles field mappings
 * @param {Object} hospital - Raw hospital data from API
 * @returns {Object} Normalized hospital object
 */
export const normalizeHospital = (hospital) => {
  if (!hospital) return null;

  const minPrice = hospital.min_price || hospital.minPrice || 0;
  const maxPrice = hospital.max_price || hospital.maxPrice || 0;
  const avgPrice = minPrice && maxPrice ? (minPrice + maxPrice) / 2 : 0;
  const marketAverage = avgPrice > 0 ? avgPrice * 1.2 : avgPrice;

  return {
    // Identifiers
    id: hospital.id || '',
    name: hospital.name || 'Unknown Hospital',
    city: hospital.city || 'Unknown City',
    location: hospital.location || hospital.city || '',

    // Scores and ratings
    aiScore: hospital.ai_score || hospital.aiScore || 85,
    rating: hospital.avg_rating || hospital.rating || hospital.success_rate || 0,
    successRate: hospital.success_rate || hospital.successRate || 0,
    patientRating: hospital.patient_rating || hospital.patientRating || 0,

    // Pricing
    pricing: {
      min: minPrice,
      max: maxPrice,
      total: avgPrice,
      marketAverage: marketAverage,
      currency: hospital.pricing?.currency || hospital.currency || 'INR'
    },

    // Stats
    stats: {
      successRate: hospital.success_rate || hospital.successRate || 0,
      distance: hospital.distance || hospital.stats?.distance || 0,
      proceduresPerYear: hospital.procedures_per_year || hospital.proceduresPerYear || 0,
      avgStayDays: hospital.avg_stay_days || hospital.avgStayDays || 0,
    },

    // Arrays - Parse if string
    specialties: parseJsonField(hospital.specialties, []),
    procedures: parseJsonField(hospital.procedures, []),
    insurance: parseJsonField(hospital.insurance, []),
    accreditations: parseJsonField(hospital.accreditations, []),

    // Contact info
    phone: hospital.phone || '',
    email: hospital.email || '',
    address: hospital.address || '',

    // URLs and coordinates
    googleMapsUrl: hospital.google_maps_url || hospital.googleMapsUrl || '#',
    heroImage: hospital.hero_image || hospital.heroImage || null,
    coordinates: hospital.coordinates || { lat: 0, lng: 0 },

    // Original data preserved
    ...hospital
  };
};

/**
 * Normalize multiple hospitals
 * @param {Array} hospitals - Array of raw hospital data
 * @returns {Array} Array of normalized hospitals
 */
export const normalizeHospitals = (hospitals) => {
  if (!Array.isArray(hospitals)) return [];
  return hospitals.map(normalizeHospital).filter(h => h !== null);
};

/**
 * Calculate savings percentage
 * @param {number} hospitalPrice - Hospital price
 * @param {number} marketAverage - Market average price
 * @returns {number} Savings percentage (0-100)
 */
export const calculateSavingsPercent = (hospitalPrice, marketAverage) => {
  if (!marketAverage || hospitalPrice >= marketAverage) return 0;
  const savings = ((marketAverage - hospitalPrice) / marketAverage) * 100;
  return Math.round(savings);
};

/**
 * Format price to Indian currency format
 * @param {number} price - Price in INR
 * @returns {string} Formatted price string
 */
export const formatPrice = (price) => {
  if (!price) return '₹0';
  const formatter = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
  });
  return formatter.format(price);
};

/**
 * Sort hospitals by criteria
 * @param {Array} hospitals - Array of hospitals
 * @param {string} sortBy - Sort criteria: 'score', 'rating', 'price', 'distance'
 * @param {boolean} ascending - Sort order
 * @returns {Array} Sorted hospitals
 */
export const sortHospitals = (hospitals, sortBy = 'score', ascending = false) => {
  const sorted = [...hospitals];
  
  const compareFn = (a, b) => {
    let valA, valB;
    
    switch (sortBy) {
      case 'score':
        valA = a.aiScore || 0;
        valB = b.aiScore || 0;
        break;
      case 'rating':
        valA = a.rating || 0;
        valB = b.rating || 0;
        break;
      case 'price':
        valA = a.pricing?.total || 0;
        valB = b.pricing?.total || 0;
        break;
      case 'distance':
        valA = a.stats?.distance || 999;
        valB = b.stats?.distance || 999;
        break;
      default:
        return 0;
    }
    
    return ascending ? valA - valB : valB - valA;
  };

  sorted.sort(compareFn);
  return sorted;
};

/**
 * Filter hospitals by criteria
 * @param {Array} hospitals - Array of hospitals
 * @param {Object} filters - Filter criteria
 * @returns {Array} Filtered hospitals
 */
export const filterHospitals = (hospitals, filters = {}) => {
  return hospitals.filter(hospital => {
    // Filter by specialty
    if (filters.specialty && !hospital.specialties?.includes(filters.specialty)) {
      return false;
    }

    // Filter by city
    if (filters.city && hospital.city?.toLowerCase() !== filters.city.toLowerCase()) {
      return false;
    }

    // Filter by min rating
    if (filters.minRating && hospital.rating < filters.minRating) {
      return false;
    }

    // Filter by max rating
    if (filters.maxRating && hospital.rating > filters.maxRating) {
      return false;
    }

    // Filter by min price
    if (filters.minPrice && hospital.pricing?.min < filters.minPrice) {
      return false;
    }

    // Filter by max price
    if (filters.maxPrice && hospital.pricing?.max > filters.maxPrice) {
      return false;
    }

    // Filter by distance
    if (filters.maxDistance && hospital.stats?.distance > filters.maxDistance) {
      return false;
    }

    // Filter by accreditation
    if (filters.accreditation && !hospital.accreditations?.includes(filters.accreditation)) {
      return false;
    }

    return true;
  });
};

/**
 * Get top N hospitals by score
 * @param {Array} hospitals - Array of hospitals
 * @param {number} limit - Number of top hospitals to return
 * @returns {Array} Top N hospitals
 */
export const getTopHospitals = (hospitals, limit = 5) => {
  if (!Array.isArray(hospitals)) return [];
  return hospitals
    .sort((a, b) => (b.aiScore || 0) - (a.aiScore || 0))
    .slice(0, Math.max(1, limit));
};

/**
 * Get hospital by ID from array
 * @param {Array} hospitals - Array of hospitals
 * @param {string} id - Hospital ID
 * @returns {Object|null} Hospital object or null
 */
export const getHospitalById = (hospitals, id) => {
  return hospitals.find(h => h.id === id) || null;
};
