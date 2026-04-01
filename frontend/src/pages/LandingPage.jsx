import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { fetchHospitalsData, analyzeQuery, isMedicalQuery } from '../utils/dummyAI';
import { API_ENDPOINTS } from '../config';

export const LandingPage = () => {
    const navigate = useNavigate();

    const [searchQuery, setSearchQuery] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [loadingStep, setLoadingStep] = useState('');
    const [uploadResult, setUploadResult] = useState(null);  // {type, text}
    const [isUploading, setIsUploading] = useState(false);

    // File input refs
    const fileInputRef = useRef(null);
    const xrayInputRef = useRef(null);
    const docInputRef = useRef(null);

    const handleFileClick = () => fileInputRef.current.click();

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) setSearchQuery(`[Attached: ${file.name}] ${searchQuery}`);
    };

    // Upload to backend and show result inline
    const handleUpload = async (file, endpoint, label) => {
        if (!file) return;
        setIsUploading(true);
        setUploadResult({ type: 'loading', text: `Analysing ${label}…` });
        try {
            const form = new FormData();
            form.append('file', file);
            form.append('session_id', `upload-${Date.now()}`);
            const res = await fetch(endpoint, { method: 'POST', body: form });
            if (!res.ok) throw new Error(`Server error ${res.status}`);
            const data = await res.json();
            const text = data.summary || data.findings || data.result || 'Analysis complete.';
            setUploadResult({ type: 'success', text });
        } catch (err) {
            setUploadResult({ type: 'error', text: `Upload failed: ${err.message}` });
        } finally {
            setIsUploading(false);
        }
    };

    const [validationError, setValidationError] = useState('');

    const runAnalysis = async (query) => {
        setIsAnalyzing(true);
        setValidationError('');
        setLoadingStep("Connecting to hospital database...");
        try {
            const allHospitals = await fetchHospitalsData();
            setLoadingStep("Extracting medical entities & parsing constraints...");
            await new Promise(r => setTimeout(r, 600));
            setLoadingStep("Cross-referencing clinical outcomes & pricing...");
            const matchedResults = analyzeQuery(query, allHospitals);
            await new Promise(r => setTimeout(r, 700));
            setLoadingStep("Finalizing 'Jolly Holidays' itinerary...");
            await new Promise(r => setTimeout(r, 500));
            navigate('/search', { state: { query, results: matchedResults } });
        } catch (error) {
            console.error("Error fetching data:", error);
            setLoadingStep("Error connecting to database. Try again.");
            setTimeout(() => setIsAnalyzing(false), 2000);
        }
    };

    const handleAnalyze = async () => {
        const q = searchQuery.trim();
        if (!q) return;
        if (!isMedicalQuery(q)) {
            setValidationError("Please enter a medical condition, procedure, or city — e.g. 'knee replacement in Chennai' or 'cardiac surgery Coimbatore'.");
            return;
        }
        setValidationError('');
        runAnalysis(q);
    };

    // Used by specialty cards and nav buttons — fetch all then navigate with preset query
    const browseTo = async (presetQuery) => {
        setSearchQuery(presetQuery);
        runAnalysis(presetQuery);
    };

    return (
        <div className="bg-background min-h-screen">
            <Navbar />
            <main className="pt-24">
                {/* Hero Section */}
                <section className="relative min-h-[70vh] flex flex-col items-center justify-center px-12 text-center overflow-hidden">
                    <div className="absolute inset-0 z-0 opacity-10 pointer-events-none">
                        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary blur-[120px] rounded-full"></div>
                        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary blur-[120px] rounded-full"></div>
                    </div>
                    
                    <div className="relative z-10 max-w-5xl mx-auto w-full -mt-10">
                        <span className="font-sans text-xs uppercase tracking-[0.3em] text-on-surface-variant mb-6 block">Global Surgical Network</span>
                        <h1 className="font-headline text-6xl md:text-8xl text-primary leading-[1.1] mb-10 italic">
                            Find and book the world's <br/>best surgeries, <span className="text-secondary">instantly.</span>
                        </h1>
                        
                        {/* Chatbot / Search Interface */}
                        <div className="max-w-3xl mx-auto bg-surface-container-lowest p-2 rounded-2xl shadow-[0_12px_32px_rgba(26,28,28,0.06)] border border-outline-variant/10 min-h-35 flex flex-col justify-center transition-all duration-500">
                            
                            {isAnalyzing ? (
                                /* Active Loading State */
                                <div className="flex flex-col items-center justify-center py-6 px-6 animate-pulse">
                                    <span className="material-symbols-outlined text-secondary animate-spin text-4xl mb-4" style={{fontVariationSettings: "'wght' 200"}}>progress_activity</span>
                                    <h3 className="text-xl font-headline text-primary italic mb-2">{loadingStep}</h3>
                                    <div className="w-64 h-1 bg-surface-variant rounded-full overflow-hidden mt-2">
                                        <div className="h-full bg-secondary rounded-full w-full origin-left transition-all duration-1000"></div>
                                    </div>
                                </div>
                            ) : (
                                /* Default Input State */
                                <>
                                    <div className="flex flex-col md:flex-row items-center gap-2">
                                        <div className="flex-1 flex items-center px-4 py-4 w-full gap-1">

                                            {/* Attach general file */}
                                            <button onClick={handleFileClick}
                                                className="text-outline hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-container-low flex items-center justify-center shrink-0"
                                                title="Attach medical report (PDF)">
                                                <span className="material-symbols-outlined text-[22px]">attach_file</span>
                                            </button>

                                            {/* X-Ray Upload */}
                                            <button onClick={() => xrayInputRef.current.click()}
                                                disabled={isUploading}
                                                className="text-outline hover:text-secondary transition-colors p-2 rounded-full hover:bg-surface-container-low flex items-center justify-center shrink-0 disabled:opacity-40"
                                                title="Upload X-Ray for AI analysis">
                                                <span className="material-symbols-outlined text-[22px]">radiology</span>
                                            </button>

                                            {/* Document / Prescription Scan */}
                                            <button onClick={() => docInputRef.current.click()}
                                                disabled={isUploading}
                                                className="text-outline hover:text-secondary transition-colors p-2 rounded-full hover:bg-surface-container-low flex items-center justify-center shrink-0 disabled:opacity-40"
                                                title="Scan prescription / medical document">
                                                <span className="material-symbols-outlined text-[22px]">description</span>
                                            </button>

                                            {/* Hidden inputs */}
                                            <input type="file" ref={fileInputRef} onChange={handleFileChange}
                                                className="hidden" accept=".pdf,image/*,.dicom" />
                                            <input type="file" ref={xrayInputRef}
                                                onChange={e => handleUpload(e.target.files[0], API_ENDPOINTS.ANALYZE_XRAY, 'X-ray')}
                                                className="hidden" accept="image/*,.dcm,.dicom" />
                                            <input type="file" ref={docInputRef}
                                                onChange={e => handleUpload(e.target.files[0], API_ENDPOINTS.PARSE_PRESCRIPTION, 'document')}
                                                className="hidden" accept=".pdf,image/*" />

                                            {/* Text Input */}
                                            <input
                                                className="bg-transparent border-none focus:ring-0 outline-none w-full font-body text-lg placeholder:text-outline-variant ml-2"
                                                placeholder="E.g., Knee replacement under ₹5L in Chennai..."
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                                            />
                                        </div>

                                        {/* Analyze Button */}
                                        <button onClick={handleAnalyze} disabled={!searchQuery.trim()}
                                            className={`w-full md:w-auto px-10 py-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all duration-300 ${
                                                searchQuery.trim()
                                                ? 'bg-primary text-on-primary hover:opacity-90 hover:shadow-lg cursor-pointer'
                                                : 'bg-surface-variant text-outline opacity-60 cursor-not-allowed'
                                            }`}>
                                            <span className="material-symbols-outlined text-sm" style={{fontVariationSettings: "'FILL' 1"}}>bolt</span>
                                            Analyze
                                        </button>
                                    </div>

                                    {/* Validation error */}
                                    {validationError && (
                                        <div className="mx-4 mb-2 px-4 py-3 rounded-xl text-sm flex items-start gap-3 bg-error-container text-on-error-container">
                                            <span className="material-symbols-outlined text-[18px] shrink-0 mt-0.5">error</span>
                                            <span>{validationError}</span>
                                            <button onClick={() => setValidationError('')} className="ml-auto shrink-0 opacity-60 hover:opacity-100">
                                                <span className="material-symbols-outlined text-[16px]">close</span>
                                            </button>
                                        </div>
                                    )}

                                    {/* Upload result banner */}
                                    {uploadResult && (
                                        <div className={`mx-4 mb-2 px-4 py-3 rounded-xl text-sm flex items-start gap-3 ${
                                            uploadResult.type === 'error'
                                                ? 'bg-error-container text-on-error-container'
                                                : uploadResult.type === 'loading'
                                                ? 'bg-surface-variant text-on-surface-variant animate-pulse'
                                                : 'bg-secondary-container text-on-secondary-container'
                                        }`}>
                                            <span className="material-symbols-outlined text-[18px] shrink-0 mt-0.5">
                                                {uploadResult.type === 'error' ? 'error' : uploadResult.type === 'loading' ? 'progress_activity' : 'check_circle'}
                                            </span>
                                            <span className="line-clamp-3">{uploadResult.text}</span>
                                            {uploadResult.type !== 'loading' && (
                                                <button onClick={() => setUploadResult(null)} className="ml-auto shrink-0 opacity-60 hover:opacity-100">
                                                    <span className="material-symbols-outlined text-[16px]">close</span>
                                                </button>
                                            )}
                                        </div>
                                    )}

                                    {/* Status Footer */}
                                    <div className="flex flex-wrap justify-center gap-6 px-6 py-4 border-t border-outline-variant/10">
                                        <div className="flex items-center text-xs font-sans tracking-widest uppercase text-outline">
                                            <span className="w-2 h-2 bg-secondary rounded-full mr-2"></span>
                                            Connected to 51 Tamil Nadu Hospitals
                                        </div>
                                        <div className="flex items-center text-xs font-sans tracking-widest uppercase text-outline">
                                            <span className="material-symbols-outlined text-[14px] mr-1">radiology</span>
                                            MedGemma Vision
                                        </div>
                                        <div className="flex items-center text-xs font-sans tracking-widest uppercase text-outline">
                                            <span className="material-symbols-outlined text-[14px] mr-1">lock</span>
                                            HIPAA Compliant
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </section>

                {/* Statistics Section */}
                <section className="bg-surface-container-low py-24 px-12">
                    <div className="max-w-screen-2xl mx-auto">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
                            {[
                                { val: "50+", label: "Verified Partner Hospitals" },
                                { val: "16%", label: "Avg. Negotiated Savings" },
                                { val: "97.5%", label: "Clinical Success Rating" }
                            ].map((stat, i) => (
                                <div key={i} className="flex flex-col items-center text-center space-y-4">
                                    <span className="font-headline text-8xl text-primary italic font-light tracking-tighter">{stat.val.replace(/[+%]/, '')}<span className="text-4xl align-top text-secondary">{stat.val.match(/[+%]/)}</span></span>
                                    <div className="h-px w-12 bg-outline-variant/30"></div>
                                    <p className="font-sans text-xs uppercase tracking-widest text-on-surface-variant">{stat.label}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Featured Data Integration Grid */}
                <section className="py-32 px-12 max-w-screen-2xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-8">
                        <div className="max-w-2xl">
                            <h2 className="font-headline text-5xl text-primary italic mb-6 leading-tight">Elite Specialties & Centers of Excellence</h2>
                            <p className="text-on-surface-variant text-lg">Curated access to Tamil Nadu's most distinguished medical departments, fully integrated with FHIR data feeds and transparent outcome metrics.</p>
                        </div>
                        <button className="group flex items-center gap-3 text-primary font-bold uppercase tracking-widest text-xs border-b border-primary pb-2 hover:border-secondary transition-all" onClick={() => browseTo('top hospitals Tamil Nadu')}>
                            Browse All 51 Facilities
                            <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">arrow_forward</span>
                        </button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-8 h-auto md:h-200">
                        {/* Apollo Chennai - Cardiology */}
                        <div className="md:col-span-8 relative group overflow-hidden rounded-xl bg-primary-container cursor-pointer" onClick={() => browseTo('cardiac surgery Chennai')}>
                            <img alt="Apollo Hospitals Chennai" className="absolute inset-0 w-full h-full object-cover opacity-50 group-hover:scale-105 transition-transform duration-700" src="https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?q=80&w=1000&auto=format&fit=crop"/>
                            <div className="absolute inset-0 bg-linear-to-t from-primary/90 via-transparent to-transparent"></div>
                            <div className="absolute bottom-0 left-0 p-12 w-full">
                                <div className="flex items-center gap-4 mb-4">
                                    <span className="material-symbols-outlined text-secondary-fixed text-3xl">cardiology</span>
                                    <span className="bg-secondary-fixed text-on-secondary-container px-2 py-0.5 text-[10px] uppercase font-bold rounded">Apollo Greams Road</span>
                                </div>
                                <h3 className="font-headline text-4xl text-on-primary italic mb-2">Cardiology</h3>
                                <p className="text-on-primary-container max-w-md">Precision cardiac interventions and valve replacement via Da Vinci Robotic Systems and Advanced Cath Labs.</p>
                            </div>
                        </div>
                        
                        {/* Ganga Hospital - Orthopedics */}
                        <div className="md:col-span-4 relative group overflow-hidden rounded-xl bg-surface-container-high cursor-pointer" onClick={() => browseTo('knee replacement orthopaedics Coimbatore')}>
                            <div className="p-10 h-full flex flex-col justify-between">
                                <div>
                                    <div className="flex justify-between items-start mb-6">
                                        <span className="material-symbols-outlined text-primary text-4xl">orthopedics</span>
                                        <span className="border border-primary/20 text-primary px-2 py-0.5 text-[10px] uppercase font-bold rounded">Ganga Hospital</span>
                                    </div>
                                    <h3 className="font-headline text-3xl text-primary italic mb-4">Orthopaedics</h3>
                                    <p className="text-on-surface-variant text-sm leading-relaxed">Joint preservation and advanced arthroplasty using Mako SmartRobotics & 3D Spine Navigation.</p>
                                </div>
                                <div className="mt-8">
                                    <ul className="space-y-3">
                                        <li className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                                            <span className="w-1.5 h-1.5 bg-secondary rounded-full"></span> Revision Knee Replacement
                                        </li>
                                        <li className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                                            <span className="w-1.5 h-1.5 bg-secondary rounded-full"></span> Complex Spine Surgery
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        {/* Apollo Proton Cancer Centre - Oncology */}
                        <div className="md:col-span-5 relative group overflow-hidden rounded-xl bg-surface-container-low cursor-pointer" onClick={() => browseTo('cancer oncology treatment Chennai')}>
                            <img alt="Apollo Proton Cancer Centre" className="absolute inset-0 w-full h-full object-cover opacity-20" src="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=1000&auto=format&fit=crop"/>
                            <div className="relative p-12">
                                <div className="flex justify-between items-start mb-6">
                                    <span className="material-symbols-outlined text-primary text-4xl">oncology</span>
                                    <span className="bg-primary/10 text-primary px-2 py-0.5 text-[10px] uppercase font-bold rounded">Apollo Proton</span>
                                </div>
                                <h3 className="font-headline text-3xl text-primary italic mb-4">Oncology</h3>
                                <p className="text-on-surface-variant text-sm leading-relaxed mb-8">South Asia's first Proton Therapy center utilizing Varian TrueBeam Linear Accelerators.</p>
                                <button onClick={(e) => { e.stopPropagation(); browseTo('cancer oncology treatment Chennai'); }} className="bg-surface-container-lowest px-6 py-3 rounded text-primary text-xs font-bold uppercase tracking-widest shadow-sm hover:bg-surface-variant transition-colors">View Outcomes</button>
                            </div>
                        </div>
                        
                        {/* Dr Rela Institute - Neurology & Transplants */}
                        <div className="md:col-span-7 relative group overflow-hidden rounded-xl bg-primary cursor-pointer" onClick={() => browseTo('neuro brain transplant surgery Chennai')}>
                            <div className="flex flex-col md:flex-row h-full">
                                <div className="md:w-1/2 p-12 flex flex-col justify-center">
                                    <div className="flex items-center gap-4 mb-6">
                                        <span className="material-symbols-outlined text-secondary-fixed text-4xl">neurology</span>
                                        <span className="border border-secondary-fixed/30 text-secondary-fixed px-2 py-0.5 text-[10px] uppercase font-bold rounded">Dr. Rela Institute</span>
                                    </div>
                                    <h3 className="font-headline text-3xl text-on-primary italic mb-4">Neurosurgery & Transplants</h3>
                                    <p className="text-on-primary-container text-sm leading-relaxed">Pioneering multi-organ transplants and complex neuro-restoration under the guidance of Prof. Mohamed Rela.</p>
                                </div>
                                <div className="md:w-1/2 relative bg-surface-variant/10">
                                    <img alt="Dr. Rela Institute" className="w-full h-full object-cover mix-blend-overlay" src="https://images.unsplash.com/photo-1538108149393-cebb47ac0925?q=80&w=1000&auto=format&fit=crop"/>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Footer Quote */}
                <section className="bg-[#e3e2e1] py-32 px-12">
                    <div className="max-w-4xl mx-auto text-center">
                        <div className="w-1 h-12 bg-primary mx-auto mb-8"></div>
                        <h2 className="font-headline text-5xl text-primary italic mb-8">"The standard of care is no longer limited by geography, but by the quality of the dossier."</h2>
                        <p className="font-sans text-xs uppercase tracking-[0.4em] text-on-surface-variant">— Clinical Standards Board, 2026</p>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
};