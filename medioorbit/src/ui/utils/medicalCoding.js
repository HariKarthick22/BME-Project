/**
 * Medical Coding and Diagnosis Utilities
 * Handles ICD-10 codes, medical procedures, and diagnosis extraction
 */

// Common ICD-10 codes for medical procedures
export const ICD10_CODES = {
  // Orthopedic procedures
  'knee-replacement': {
    code: '0SRC0ZZ',
    description: 'Replacement of Right Knee Joint with Synthetic Substitute',
    category: 'Orthopedic',
    specialty: 'Orthopedics',
    estPrice: { min: 250000, max: 500000 }
  },
  'hip-replacement': {
    code: '0SRB0ZZ',
    description: 'Replacement of Right Hip Joint with Synthetic Substitute',
    category: 'Orthopedic',
    specialty: 'Orthopedics',
    estPrice: { min: 300000, max: 600000 }
  },
  'spine-fusion': {
    code: '0SG60ZZ',
    description: 'Fusion of Lumbar Vertebral Joint',
    category: 'Orthopedic',
    specialty: 'Spine Surgery',
    estPrice: { min: 400000, max: 750000 }
  },

  // Cardiac procedures
  'cabg-surgery': {
    code: '0210083',
    description: 'Bypass Grafting, Right Internal Mammary Artery to Coronary',
    category: 'Cardiac',
    specialty: 'Cardiac Surgery',
    estPrice: { min: 500000, max: 1200000 }
  },
  'angioplasty': {
    code: '027E3ZZ',
    description: 'Dilation of Coronary Artery with Drug-eluting Stent',
    category: 'Cardiac',
    specialty: 'Interventional Cardiology',
    estPrice: { min: 120000, max: 300000 }
  },
  'pacemaker-implant': {
    code: '0JH60RZ',
    description: 'Insertion of Permanent Pacemaker in Chest',
    category: 'Cardiac',
    specialty: 'Cardiac Surgery',
    estPrice: { min: 150000, max: 400000 }
  },

  // Neurological procedures
  'brain-tumor-surgery': {
    code: '00B00ZX',
    description: 'Excision of Brain Lesion, Open Approach',
    category: 'Neurological',
    specialty: 'Neurosurgery',
    estPrice: { min: 600000, max: 1500000 }
  },
  'vp-shunt': {
    code: '0JH60ZZ',
    description: 'Insertion of Ventriculoperitoneal Shunt',
    category: 'Neurological',
    specialty: 'Neurosurgery',
    estPrice: { min: 200000, max: 500000 }
  },

  // Renal procedures
  'kidney-transplant': {
    code: '0TY00Z0',
    description: 'Transplantation of Right Kidney',
    category: 'Renal',
    specialty: 'Nephrology',
    estPrice: { min: 800000, max: 2000000 }
  },
  'dialysis-setup': {
    code: '5A1D60Z',
    description: 'Hemodialysis Treatment',
    category: 'Renal',
    specialty: 'Nephrology',
    estPrice: { min: 5000, max: 15000 }
  }
};

// Medical procedure categories
export const PROCEDURE_CATEGORIES = {
  'orthopedic': ['knee-replacement', 'hip-replacement', 'spine-fusion'],
  'cardiac': ['cabg-surgery', 'angioplasty', 'pacemaker-implant'],
  'neurological': ['brain-tumor-surgery', 'vp-shunt'],
  'renal': ['kidney-transplant', 'dialysis-setup'],
  'general': ['appendectomy', 'cholecystectomy']
};

// Medical specialty mapping
export const SPECIALTY_PROCEDURES = {
  'Orthopedics': ['knee-replacement', 'hip-replacement', 'spine-fusion'],
  'Cardiac Surgery': ['cabg-surgery', 'pacemaker-implant'],
  'Interventional Cardiology': ['angioplasty'],
  'Neurosurgery': ['brain-tumor-surgery', 'vp-shunt'],
  'Nephrology': ['kidney-transplant', 'dialysis-setup'],
};

// Common diagnoses (ICD-10)
export const DIAGNOSIS_CODES = {
  'M17.11': { text: 'Primary osteoarthritis, right knee', category: 'Orthopedic' },
  'I25.10': { text: 'Atherosclerotic heart disease', category: 'Cardiac' },
  'R06.02': { text: 'Shortness of breath', category: 'General' },
  'R07.2': { text: 'Precordial pain', category: 'Cardiac' },
  'G89.29': { text: 'Other chronic pain', category: 'Neurological' },
  'N18.3': { text: 'Chronic kidney disease, stage 3', category: 'Renal' },
};

/**
 * Get procedure details by code
 * @param {string} procedureKey - Procedure identifier
 * @returns {Object} Procedure details with ICD-10 code and info
 */
export const getProcedureDetails = (procedureKey) => {
  return ICD10_CODES[procedureKey.toLowerCase()] || null;
};

/**
 * Extract diagnosis from medical text
 * @param {string} text - Medical text/prescription content
 * @returns {Array} Extracted diagnoses with codes
 */
export const extractDiagnosis = (text) => {
  if (!text) return [];

  const diagnoses = [];
  const keywords = {
    'knee pain': 'M17.11',
    'arthritis': 'M17.11',
    'heart disease': 'I25.10',
    'chest pain': 'R07.2',
    'shortness of breath': 'R06.02',
    'kidney disease': 'N18.3',
    'dialysis': 'N18.3'
  };

  Object.entries(keywords).forEach(([keyword, code]) => {
    if (text.toLowerCase().includes(keyword)) {
      diagnoses.push({
        code,
        text: DIAGNOSIS_CODES[code]?.text || keyword,
        category: DIAGNOSIS_CODES[code]?.category || 'General'
      });
    }
  });

  return diagnoses;
};

/**
 * Extract medications from medical text
 * @param {string} text - Medical text/prescription content
 * @returns {Array} Extracted medications
 */
export const extractMedications = (text) => {
  if (!text) return [];

  const medications = [];
  const commonMeds = [
    'aspirin', 'paracetamol', 'ibuprofen', 'metformin', 'atorvastatin',
    'lisinopril', 'amlodipine', 'metoprolol', 'warfarin', 'clopidogrel'
  ];

  commonMeds.forEach(med => {
    if (text.toLowerCase().includes(med)) {
      medications.push({
        name: med.charAt(0).toUpperCase() + med.slice(1),
        strength: extractStrength(text, med),
        frequency: extractFrequency(text)
      });
    }
  });

  return medications;
};

/**
 * Extract medication strength from text
 * @param {string} text - Medical text
 * @param {string} medication - Medication name
 * @returns {string} Extracted strength
 */
const extractStrength = (text, medication) => {
  const regex = new RegExp(`${medication}\\s+(\\d+)\\s*(mg|ml|g)`, 'gi');
  const match = text.match(regex);
  return match ? match[0].split(medication)[1].trim() : '';
};

/**
 * Extract medication frequency from text
 * @param {string} text - Medical text
 * @returns {string} Frequency description
 */
const extractFrequency = (text) => {
  const frequencyPatterns = ['once daily', 'twice daily', 'thrice daily', 'every morning', 'every night', 'as needed'];
  for (const pattern of frequencyPatterns) {
    if (text.toLowerCase().includes(pattern)) {
      return pattern;
    }
  }
  return 'as prescribed';
};

/**
 * Extract procedures from medical text
 * @param {string} text - Medical text/prescription content
 * @returns {Array} Extracted procedures
 */
export const extractProcedures = (text) => {
  if (!text) return [];

  const procedures = [];
  Object.entries(ICD10_CODES).forEach(([key, details]) => {
    if (text.toLowerCase().includes(key.replace('-', ' ')) ||
        text.toLowerCase().includes(details.description.toLowerCase())) {
      procedures.push(details);
    }
  });

  return procedures;
};

/**
 * Get medical coding summary from extracted data
 * @param {Object} extracted - Extracted data with diagnoses, medications, procedures
 * @returns {Object} Medical coding summary
 */
export const getMedicalCodingSummary = (extracted) => {
  return {
    diagnoses: extracted.diagnoses || [],
    medications: extracted.medications || [],
    procedures: extracted.procedures || [],
    codes: [
      ...(extracted.diagnoses?.map(d => d.code) || []),
      ...(extracted.procedures?.map(p => p.code) || [])
    ].filter(Boolean),
    estimatedComplexity: calculateComplexity(extracted),
    estimatedCost: estimateProcedureCost(extracted)
  };
};

/**
 * Calculate medical case complexity
 * @param {Object} extracted - Extracted medical data
 * @returns {string} Complexity level
 */
const calculateComplexity = (extracted) => {
  const diagnosisCount = (extracted.diagnoses || []).length;
  const medicationCount = (extracted.medications || []).length;
  const procedureCount = (extracted.procedures || []).length;

  const totalFactors = diagnosisCount + medicationCount + procedureCount;

  if (totalFactors > 10) return 'High';
  if (totalFactors > 5) return 'Moderate';
  return 'Low';
};

/**
 * Estimate procedure cost range
 * @param {Object} extracted - Extracted medical data
 * @returns {Object} Cost estimation
 */
const estimateProcedureCost = (extracted) => {
  const procedures = extracted.procedures || [];
  
  if (procedures.length === 0) {
    return { min: 0, max: 0, currency: 'INR' };
  }

  const minCosts = procedures.map(p => p.estPrice?.min || 0);
  const maxCosts = procedures.map(p => p.estPrice?.max || 0);

  return {
    min: Math.min(...minCosts),
    max: Math.max(...maxCosts),
    currency: 'INR'
  };
};

/**
 * Validate medical data structure
 * @param {Object} data - Medical data to validate
 * @returns {boolean} Is valid medical data
 */
export const isValidMedicalData = (data) => {
  if (!data || typeof data !== 'object') return false;
  
  const hasText = typeof data.text === 'string' && data.text.length > 0;
  const hasExtracted = data.diagnoses || data.medications || data.procedures;
  
  return hasText && hasExtracted;
};
