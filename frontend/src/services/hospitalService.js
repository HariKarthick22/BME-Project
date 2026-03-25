/**
 * Hospital Service - Centralized API management for hospital data
 * Handles all hospital-related API calls and data transformations
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

class HospitalService {
  /**
   * Fetch all hospitals with optional filtering
   * @param {Object} params - Query parameters
   * @returns {Promise<Array>} Array of normalized hospitals
   */
  async getAllHospitals(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `${API_BASE}/hospitals${queryString ? `?${queryString}` : ''}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error('Error fetching all hospitals:', error);
      return [];
    }
  }

  /**
   * Get top N hospitals (by AI score/rating)
   * @param {number} limit - Number of hospitals to return (default: 5)
   * @returns {Promise<Array>} Top hospitals sorted by score
   */
  async getTopHospitals(limit = 5) {
    try {
      const hospitals = await this.getAllHospitals({ limit: limit * 2 });
      
      // Sort by AI score descending, then by success rate
      return hospitals
        .sort((a, b) => {
          const scoreA = a.ai_score || a.aiScore || 0;
          const scoreB = b.ai_score || b.aiScore || 0;
          const rateA = a.success_rate || a.successRate || 0;
          const rateB = b.success_rate || b.successRate || 0;
          
          if (scoreB !== scoreA) return scoreB - scoreA;
          return rateB - rateA;
        })
        .slice(0, limit);
    } catch (error) {
      console.error('Error fetching top hospitals:', error);
      return [];
    }
  }

  /**
   * Get hospitals from chat results (from sessionStorage)
   * Falls back to API if no cached results
   * @param {boolean} useCache - Use sessionStorage cache if available
   * @returns {Promise<Array>} Hospitals from cache or API
   */
  async getSearchResults(useCache = true) {
    if (useCache) {
      const cached = sessionStorage.getItem('lastSearchResults');
      if (cached) {
        try {
          const results = JSON.parse(cached);
          if (Array.isArray(results) && results.length > 0) {
            // Return top 5 from chat results
            return results.slice(0, 5);
          }
        } catch (e) {
          console.warn('Failed to parse cached results:', e);
        }
      }
    }

    // Fallback: return top 5 hospitals from all
    return this.getTopHospitals(5);
  }

  /**
   * Get single hospital by ID
   * @param {string} id - Hospital ID
   * @returns {Promise<Object>} Hospital data or null
   */
  async getHospitalById(id) {
    try {
      const response = await fetch(`${API_BASE}/hospitals/${id}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching hospital ${id}:`, error);
      return null;
    }
  }

  /**
   * Search hospitals by specialty/procedure
   * @param {string} specialty - Medical specialty to search for
   * @returns {Promise<Array>} Matching hospitals
   */
  async searchBySpecialty(specialty) {
    try {
      return await this.getAllHospitals({ specialty });
    } catch (error) {
      console.error('Error searching by specialty:', error);
      return [];
    }
  }

  /**
   * Search hospitals by city
   * @param {string} city - City name
   * @returns {Promise<Array>} Hospitals in city
   */
  async searchByCity(city) {
    try {
      return await this.getAllHospitals({ city });
    } catch (error) {
      console.error('Error searching by city:', error);
      return [];
    }
  }

  /**
   * Filter hospitals by price range
   * @param {number} minPrice - Minimum price
   * @param {number} maxPrice - Maximum price
   * @returns {Promise<Array>} Hospitals within price range
   */
  async filterByPrice(minPrice, maxPrice) {
    try {
      return await this.getAllHospitals({ min_price: minPrice, max_price: maxPrice });
    } catch (error) {
      console.error('Error filtering by price:', error);
      return [];
    }
  }

  /**
   * Store chat results in sessionStorage for quick access
   * @param {Array} hospitals - Hospital results to cache
   */
  cacheSearchResults(hospitals) {
    try {
      sessionStorage.setItem('lastSearchResults', JSON.stringify(hospitals));
    } catch (error) {
      console.warn('Failed to cache results:', error);
    }
  }
}

export const hospitalService = new HospitalService();
export default HospitalService;
