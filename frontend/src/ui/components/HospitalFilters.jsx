import React, { useState } from 'react';

export const HospitalFilters = ({ filters, onFilterChange, onClearFilters }) => {
  const [expandedSection, setExpandedSection] = useState(null);

  const handleFilterChange = (filterName, value) => {
    onFilterChange(filterName, value);
  };

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const specialties = [
    'Cardiology',
    'Orthopedics',
    'Neurology',
    'Oncology',
    'Gastroenterology',
    'Nephrology',
    'Urology',
    'Ophthalmology',
    'ENT',
    'Pediatrics',
    'General Surgery',
    'Spine Surgery'
  ];

  const cities = [
    'Chennai',
    'Coimbatore',
    'Madurai',
    'Salem',
    'Trichy',
    'Erode',
    'Tiruppur',
    'Kanyakumari',
    'Thanjavur',
    'Pondicherry'
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Filter Results</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Specialty Filter */}
        <div>
          <button
            onClick={() => toggleSection('specialty')}
            className="w-full text-left font-semibold text-gray-900 pb-3 border-b-2 border-gray-200 hover:border-blue-600 transition-colors"
          >
            Specialty
            <span className="float-right text-gray-600">
              {expandedSection === 'specialty' ? '▼' : '▶'}
            </span>
          </button>
          {expandedSection === 'specialty' && (
            <div className="mt-4 space-y-2">
              <input
                type="text"
                placeholder="Search specialty..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                onChange={(e) => handleFilterChange('specialty', e.target.value)}
                value={filters.specialty}
              />
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {specialties.map(specialty => (
                  <label key={specialty} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="specialty"
                      className="rounded"
                      checked={filters.specialty === specialty}
                      onChange={() => handleFilterChange('specialty', specialty)}
                    />
                    <span className="text-sm text-gray-700">{specialty}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* City Filter */}
        <div>
          <button
            onClick={() => toggleSection('city')}
            className="w-full text-left font-semibold text-gray-900 pb-3 border-b-2 border-gray-200 hover:border-blue-600 transition-colors"
          >
            City
            <span className="float-right text-gray-600">
              {expandedSection === 'city' ? '▼' : '▶'}
            </span>
          </button>
          {expandedSection === 'city' && (
            <div className="mt-4 space-y-2">
              <input
                type="text"
                placeholder="Search city..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                value={filters.city}
                onChange={(e) => handleFilterChange('city', e.target.value)}
              />
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {cities.map(city => (
                  <label key={city} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="city"
                      className="rounded"
                      checked={filters.city === city}
                      onChange={() => handleFilterChange('city', city)}
                    />
                    <span className="text-sm text-gray-700">{city}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Rating Filter */}
        <div>
          <button
            onClick={() => toggleSection('rating')}
            className="w-full text-left font-semibold text-gray-900 pb-3 border-b-2 border-gray-200 hover:border-blue-600 transition-colors"
          >
            Min Rating
            <span className="float-right text-gray-600">
              {expandedSection === 'rating' ? '▼' : '▶'}
            </span>
          </button>
          {expandedSection === 'rating' && (
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="0.5"
                  value={filters.minRating}
                  onChange={(e) => handleFilterChange('minRating', Number(e.target.value))}
                  className="w-full"
                />
                <div className="text-sm text-gray-600">
                  Minimum Rating: {filters.minRating} ⭐
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-gray-600">
                  Max Price (₹):
                  <input
                    type="number"
                    min="0"
                    value={filters.maxPrice}
                    onChange={(e) => handleFilterChange('maxPrice', Number(e.target.value || 0))}
                    className="w-full mt-1 px-2 py-2 border border-gray-300 rounded-md"
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Sort Filter */}
        <div>
          <button
            onClick={() => toggleSection('sort')}
            className="w-full text-left font-semibold text-gray-900 pb-3 border-b-2 border-gray-200 hover:border-blue-600 transition-colors"
          >
            Sort By
            <span className="float-right text-gray-600">
              {expandedSection === 'sort' ? '▼' : '▶'}
            </span>
          </button>
          {expandedSection === 'sort' && (
            <div className="mt-4 space-y-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="sort"
                  value="rating"
                  checked={filters.sortBy === 'rating'}
                  onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                  className="rounded-full"
                />
                <span className="text-sm text-gray-700">Rating (High to Low)</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="sort"
                  value="price"
                  checked={filters.sortBy === 'price'}
                  onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                  className="rounded-full"
                />
                <span className="text-sm text-gray-700">Price (Low to High)</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="sort"
                  value="distance"
                  checked={filters.sortBy === 'distance'}
                  onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                  className="rounded-full"
                />
                <span className="text-sm text-gray-700">Distance (Low to High)</span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Clear Filters Button */}
      <div className="mt-6 flex gap-4">
        <button
          onClick={() => onClearFilters()}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-medium"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
};
