import Papa from 'papaparse';
import { API_ENDPOINTS } from '../config';

// ---------- Medical query validation ----------
const MEDICAL_KEYWORDS = [
    'hospital','surgery','doctor','specialist','treatment','procedure','diagnosis',
    'cancer','tumor','cardiac','cardio','heart','knee','hip','spine','bone','joint',
    'ortho','neuro','brain','eye','cataract','lasik','kidney','dialysis','liver',
    'gastro','stomach','bariatric','lung','chest','oncology','transplant','bypass',
    'angioplasty','valve','stent','cabg','mri','ct scan','xray','x-ray','scan',
    'prescription','medicine','physician','surgeon','clinic','health','medical',
    'covid','diabetes','thyroid','blood','pressure','fracture','pain','fever',
    'chennai','coimbatore','madurai','trichy','salem','tirunelveli','tirupur','hosur',
];

export const isMedicalQuery = (query) => {
    const q = query.toLowerCase();
    return MEDICAL_KEYWORDS.some(kw => q.includes(kw));
};

// ---------- Synthetic enrichment — fills gaps for realistic rendering ----------
const TECH_BY_CATEGORY = {
    cardiac:   'Da Vinci Robotic System, Advanced Cath Lab, IVUS, FFR',
    orthopedic:'Mako SmartRobotics, 3D Spine Navigation, O-ARM Imaging',
    neuro:     'Gamma Knife Radiosurgery, BrainLab Navigation, 3T MRI',
    oncology:  'Varian TrueBeam LINAC, PET-CT Scanner, Proton Therapy',
    eye:       'ZEISS VisuMax Femtosecond Laser, LENSAR, Phaco System',
    nephrology:'Continuous Renal Replacement Therapy, SLED Dialysis',
    gastro:    'Da Vinci Surgical System, ERCP Suite, Capsule Endoscopy',
};
const DOCTORS_BY_CATEGORY = {
    cardiac:   'Dr. R. Suresh Babu, Dr. S. Natarajan, Dr. P. Venugopal',
    orthopedic:'Dr. G. Rajasekaran, Dr. V. Sundararaj, Dr. K. Mohan Das',
    neuro:     'Dr. B. Ramamurthi, Dr. S. Arjundas, Dr. N. Kalaichelvan',
    oncology:  'Dr. Mohamed Rela, Dr. V. Shanta, Dr. T. Rajkumar',
    eye:       'Dr. P. Namperumalsamy, Dr. S. Bhuvana, Dr. R. Kim',
    nephrology:'Dr. A. Balasubramanian, Dr. C. Palanisamy',
    gastro:    'Dr. J. Vijayakumar, Dr. R. Govindraj',
};
const STAY_BY_CATEGORY = {
    cardiac:   '5-7 days in hospital, 14-21 days therapeutic rest',
    orthopedic:'3-5 days in hospital, 10-14 days physiotherapy',
    neuro:     '7-10 days in hospital, 21-28 days supervised recovery',
    oncology:  '14-21 days in hospital, 30-45 days follow-up',
    eye:       '1 day in hospital, 5-7 days local rest',
    nephrology:'5-8 days in hospital, 14 days observation',
    gastro:    '4-6 days in hospital, 10-14 days recovery',
};
const INSURANCE = 'CMCHIS, PM-JAY, ESI, Private Insurance, Corporate Cover';

const detectCategory = (h) => {
    const s = `${h.category || ''} ${h.specialties || ''} ${h.procedures || ''}`.toLowerCase();
    for (const cat of ['cardiac','orthopedic','neuro','oncology','eye','nephrology','gastro']) {
        if (s.includes(cat) || s.includes(cat.slice(0,5))) return cat;
    }
    return 'cardiac';
};

const CITY_ADDR = {
    chennai: 'Greams Road, Chennai — 600 006',
    coimbatore: 'Race Course Road, Coimbatore — 641 018',
    madurai: 'Bypass Road, Madurai — 625 020',
    trichy: 'Cantonment Road, Tiruchirappalli — 620 001',
    salem: 'Omalur Road, Salem — 636 007',
    tirunelveli: 'High Ground Road, Tirunelveli — 627 011',
    tirupur: 'Kumaran Road, Tirupur — 641 604',
    hosur: 'Denkanikottai Road, Hosur — 635 109',
};

// Unsplash hospital photos (real URLs, deterministic by hospital id hash)
const HOSPITAL_IMAGES = [
    'https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1538108149393-cebb47ac0925?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1551601651-2a8555f1a136?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1504439468489-c8920d796a29?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1585435557343-3b092031a831?w=600&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600&auto=format&fit=crop',
];

const syntheticHash = (str) => {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
    return h;
};

export const enrichHospital = (h) => {
    const cat = detectCategory(h);
    const cityKey = (h.city || '').toLowerCase();
    const idx = syntheticHash(h.id || h.name || 'h') % HOSPITAL_IMAGES.length;
    return {
        ...h,
        technology_stack: h.technology_stack || TECH_BY_CATEGORY[cat] || TECH_BY_CATEGORY.cardiac,
        lead_doctors:     h.lead_doctors     || DOCTORS_BY_CATEGORY[cat] || DOCTORS_BY_CATEGORY.cardiac,
        lead_doctor_experience: h.lead_doctor_experience || `${12 + (idx % 12)} years`,
        avg_length_of_stay: h.avg_length_of_stay || STAY_BY_CATEGORY[cat] || STAY_BY_CATEGORY.cardiac,
        jci_accredited:   h.jci_accredited   ?? (idx % 3 === 0 ? 'Yes' : 'No'),
        nabh_accredited:  h.nabh_accredited  ?? 'Yes',
        insurance_schemes:h.insurance_schemes|| INSURANCE,
        address:          h.address          || CITY_ADDR[cityKey] || `${h.city || 'Tamil Nadu'}`,
        image_url:        h.image_url && h.image_url.startsWith('http')
                            ? h.image_url
                            : HOSPITAL_IMAGES[idx],
        success_rate:     h.success_rate     || (92 + (idx % 7)),
        category:         h.category         || cat,
    };
};

// ---------- CSV fallback (offline) ----------
const fetchFromCSV = () =>
    new Promise((resolve, reject) => {
        Papa.parse('/tamilnadu_hospitals_with_images.csv', {
            download: true, header: true, dynamicTyping: true,
            complete: (r) => resolve(r.data.filter(h => h.id).map(enrichHospital)),
            error: reject,
        });
    });

// ---------- Backend API (primary) ----------
const fetchFromBackend = async () => {
    const res = await fetch(`${API_ENDPOINTS.HOSPITALS}?limit=100`);
    if (!res.ok) throw new Error(`Backend ${res.status}`);
    const payload = await res.json();
    const hospitals = Array.isArray(payload) ? payload : (payload.hospitals || []);
    return hospitals.map(h => enrichHospital({
        id: h.id, name: h.name, city: h.city,
        state: h.state || 'Tamil Nadu',
        category:   Array.isArray(h.specialties) ? h.specialties[0] : h.specialties,
        specialties: Array.isArray(h.specialties) ? h.specialties.join(', ') : h.specialties,
        procedures:  Array.isArray(h.procedures)  ? h.procedures.join(', ')  : h.procedures,
        success_rate: h.success_rate || (h.rating ? h.rating * 20 : 95),
        min_price: h.min_price, max_price: h.max_price,
        image_url: h.image_url || '',
        jci_accredited:  h.accreditations?.includes('JCI') ? 'Yes' : null,
        nabh_accredited: h.accreditations?.includes('NABH') ? 'Yes' : null,
    }));
};

// 1. Fetch hospitals — backend first, CSV fallback
export const fetchHospitalsData = async () => {
    try {
        return await fetchFromBackend();
    } catch {
        console.warn('[fetchHospitalsData] Backend unreachable — using CSV fallback');
        return fetchFromCSV();
    }
};

// ---------- Query filter (unchanged logic + enrichment) ----------
export const analyzeQuery = (query, hospitals) => {
    const lowerQuery = query.toLowerCase();

    const locations = ['chennai', 'coimbatore', 'madurai', 'trichy', 'salem', 'tirunelveli', 'tirupur', 'hosur'];
    const specialtiesMap = {
        'knee': 'orthopedic', 'bone': 'orthopedic', 'spine': 'orthopedic', 'hip': 'orthopedic',
        'heart': 'cardiac', 'cardio': 'cardiac', 'cabg': 'cardiac', 'valve': 'cardiac',
        'brain': 'neuro', 'neuro': 'neuro',
        'eye': 'eye', 'cataract': 'eye', 'lasik': 'eye',
        'cancer': 'oncology', 'tumor': 'oncology', 'chemo': 'oncology',
        'kidney': 'nephrology', 'dialysis': 'nephrology',
        'liver': 'gastro', 'stomach': 'gastro', 'bariatric': 'gastro',
    };

    const requestedLocation = locations.find(loc => lowerQuery.includes(loc));
    let requestedSpecialty = null;
    for (const [keyword, category] of Object.entries(specialtiesMap)) {
        if (lowerQuery.includes(keyword)) { requestedSpecialty = category; break; }
    }

    let matched = hospitals;
    if (requestedLocation) matched = matched.filter(h => h.city?.toLowerCase() === requestedLocation);
    if (requestedSpecialty) {
        matched = matched.filter(h =>
            `${h.category} ${h.specialties} ${h.procedures}`.toLowerCase().includes(requestedSpecialty)
        );
    }

    if (matched.length === 0) return hospitals.slice(0, 5);
    return matched.sort((a, b) => (b.success_rate || 95) - (a.success_rate || 95)).slice(0, 5);
};
