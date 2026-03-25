import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import HospitalCard from '../components/HospitalCard';

export default function HospitalDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [hospital, setHospital] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) {
      navigate('/');
      return;
    }
    
    fetchHospital();
  }, [id, navigate]);

  const fetchHospital = async () => {
    try {
      const response = await fetch(`/api/hospitals/${id}`);
      const data = await response.json();
      setHospital(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching hospital:', error);
      setLoading(false);
      navigate('/');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!hospital) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Hospital not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-lg shadow mb-8 p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-900">{hospital.name}</h1>
            <div className="flex items-center space-x-2">
              <div className="text-2xl">
                <span className="text-yellow-400">★</span>
                {hospital.rating}
              </div>
              <span className="text-sm text-gray-500">({hospital.reviews || 0} reviews)</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Location</h3>
              <p className="text-gray-600">{hospital.address}</p>
              <p className="text-gray-600">{hospital.city}, {hospital.state} {hospital.zip}</p>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Contact</h3>
              <p className="text-gray-600">{hospital.phone}</p>
              <a href={`mailto:${hospital.email}`} className="text-blue-600 hover:underline">{hospital.email}</a>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Stats</h3>
              {hospital.stats && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-sm text-gray-500">Distance:</span>
                    <span className="ml-1 font-medium">{hospital.stats.distance || 'N/A'} km</span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Travel Time:</span>
                    <span className="ml-1 font-medium">{hospital.stats.travelTime || 'N/A'}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t pt-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Pricing Information</h2>
            {hospital.pricing ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-sm text-gray-600">Min Cost</div>
                  <div className="text-2xl font-bold text-blue-600">₹{hospital.pricing.minCost || 0}</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-sm text-gray-600">Max Cost</div>
                  <div className="text-2xl font-bold text-green-600">₹{hospital.pricing.maxCost || 0}</div>
                </div>
              </div>
            ) : (
              <p className="text-gray-600">No pricing information available</p>
            )}
          </div>

          <div className="border-t pt-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Specialties</h2>
            <div className="flex flex-wrap gap-2">
              {hospital.specialties && hospital.specialties.length > 0 ? (
                hospital.specialties.map((spec, idx) => (
                  <span key={idx} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                    {spec}
                  </span>
                ))
              ) : (
                <p className="text-gray-600">No specialties listed</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
