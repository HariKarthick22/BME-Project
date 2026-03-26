import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const SearchResultsPage = () => {
    const navigate = useNavigate();
    
    // Data perfectly mapped from hospitals_final.csv
    const hospitals = [
        {
            id: 'royal-care',
            name: 'Royal Care Super Speciality',
            address: '1/520, Neelambur, Avinashi Road, Coimbatore, TN 641062',
            category: 'Cardiac',
            success_rate: 97,
            avg_length_of_stay: '5 Days Hospital, 10 Days Hotel',
            lead_doctor_experience: '25+ Years',
            lead_doctors: 'Dr. Nachimuthu',
            min_price: 120000,
            max_price: 2500000,
            jci_accredited: 'Yes',
            nabh_accredited: 'Yes',
            insurance_schemes: 'CMCHIS, PM-JAY, Private Insurance',
            technology_stack: 'Da Vinci Robotic System, Advanced Cath Labs',
            img: 'https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?q=80&w=2000&auto=format&fit=crop'
        },
        {
            id: 'gknm',
            name: 'GKNM Hospital',
            address: 'P.B.No. 6327, Pappanaickenpalayam, Coimbatore, TN 641037',
            category: 'Multi-Specialty',
            success_rate: 96,
            avg_length_of_stay: '5 Days Hospital, 7 Days Hotel',
            lead_doctor_experience: '35+ Years',
            lead_doctors: 'Dr. K.A. Sambasivam, Dr. M.R. Balasenthil',
            min_price: 100000,
            max_price: 2500000,
            jci_accredited: 'No',
            nabh_accredited: 'Yes',
            insurance_schemes: 'CMCHIS, PM-JAY, Private Insurance',
            technology_stack: '4th Gen Robotic Surgery, Mitra-Clip, TAVR',
            img: 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=2000&auto=format&fit=crop'
        },
        {
            id: 'kg-hospital',
            name: 'KG Hospital',
            address: 'Arts College Road, Coimbatore, TN 641018',
            category: 'Multi-Specialty',
            success_rate: 97,
            avg_length_of_stay: '4 Days Hospital, 10 Days Hotel',
            lead_doctor_experience: '20+ Years',
            lead_doctors: 'Dr. Srinivasan, Dr. S. Raj Kumar',
            min_price: 130000,
            max_price: 600000,
            jci_accredited: 'No',
            nabh_accredited: 'Yes',
            insurance_schemes: 'CMCHIS, PM-JAY, Private Insurance',
            technology_stack: 'Da Vinci Surgical Robot, 3DHD Vision',
            img: 'https://images.unsplash.com/photo-1538108149393-cebb47ac0925?q=80&w=2000&auto=format&fit=crop'
        }
    ];

    // Helper to format currency
    const formatCurrency = (val) => `₹${(val / 100000).toFixed(1)}L`;

    return (
        <div className="bg-surface">
            <Navbar />
            <main className="pt-32 pb-24 px-12 max-w-screen-2xl mx-auto">
                {/* Search Header */}
                <div className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-8">
                    <div className="space-y-2">
                        <p className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold flex items-center gap-2">
                            <span className="w-2 h-2 bg-secondary rounded-full animate-pulse"></span>
                            AI Swarm Analysis Complete
                        </p>
                        <h1 className="font-headline text-5xl md:text-6xl text-primary leading-none">
                            Cardiac Surgery <span className="serif-italic">in Coimbatore</span>
                        </h1>
                        <div className="flex items-center gap-3 mt-4">
                            <span className="bg-surface-container-high px-3 py-1 text-xs font-semibold rounded-full text-primary">NABH Accredited</span>
                            <span className="bg-surface-container-high px-3 py-1 text-xs font-semibold rounded-full text-primary">CMCHIS / PM-JAY</span>
                            <span className="text-on-surface-variant text-sm border-l border-outline-variant pl-3">{hospitals.length} Validated Institutions</span>
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <button className="flex items-center gap-2 border border-outline-variant px-5 py-2.5 rounded hover:bg-surface-container-low transition-colors text-sm font-medium">
                            <span className="material-symbols-outlined text-sm">tune</span>
                            Adjust "Jolly" Preferences
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
                    {/* Hospital Cards List */}
                    <div className="lg:col-span-8 space-y-8">
                        {hospitals.map((h) => (
                            <div key={h.id} onClick={() => navigate('/detail', { state: { hospital: h } })} className="group cursor-pointer...">
                                <div className="flex flex-col md:flex-row gap-8">
                                    {/* Image */}
                                    <div className="w-full md:w-56 h-auto min-h-[160px] bg-surface-container overflow-hidden rounded-lg">
                                        <img alt={h.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" src={h.img}/>
                                    </div>
                                    
                                    {/* Content */}
                                    <div className="flex-1">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-2 mb-2">
                                                    {h.jci_accredited === 'Yes' && (
                                                        <span className="bg-secondary-container text-on-secondary-container text-[10px] px-2 py-0.5 font-bold rounded uppercase flex items-center gap-1">
                                                            <span className="material-symbols-outlined text-[12px]">verified</span> JCI Gold Standard
                                                        </span>
                                                    )}
                                                    {h.nabh_accredited === 'Yes' && (
                                                        <span className="border border-outline-variant/30 text-on-surface-variant text-[10px] px-2 py-0.5 font-bold rounded uppercase">
                                                            NABH
                                                        </span>
                                                    )}
                                                    <span className="text-[10px] uppercase tracking-widest text-secondary font-bold ml-2">{h.category}</span>
                                                </div>
                                                <h3 className="font-headline text-3xl text-primary mb-2">{h.name}</h3>
                                                <p className="text-on-surface-variant text-sm flex items-center gap-1 leading-snug">
                                                    <span className="material-symbols-outlined text-sm">location_on</span>
                                                    <span className="max-w-[280px] truncate" title={h.address}>{h.address}</span>
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-4xl font-headline text-secondary leading-none">{(h.success_rate / 10).toFixed(1)}<span className="text-sm font-body text-on-surface-variant ml-1">/10</span></div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mt-1">AI Clinical Score</p>
                                            </div>
                                        </div>

                                        {/* 4-Column Data Grid */}
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 py-6 border-y border-outline-variant/10">
                                            <div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Success Rate</p>
                                                <p className="text-lg font-medium text-primary">{h.success_rate}%</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Est. Stay</p>
                                                <p className="text-sm font-medium text-primary leading-tight">{h.avg_length_of_stay}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Surgeon Exp.</p>
                                                <p className="text-lg font-medium text-primary">{h.lead_doctor_experience}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Est. Cost Range</p>
                                                <p className="text-sm font-medium text-secondary leading-tight">{formatCurrency(h.min_price)} - {formatCurrency(h.max_price)}</p>
                                            </div>
                                        </div>

                                        {/* Bottom Tech & Action */}
                                        <div className="mt-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                            <div className="flex flex-col gap-1">
                                                <p className="text-[11px] text-on-surface-variant flex items-center gap-1">
                                                    <span className="material-symbols-outlined text-[14px]">memory</span>
                                                    <span className="font-semibold text-primary">Tech:</span> {h.technology_stack}
                                                </p>
                                                <p className="text-[11px] text-on-surface-variant flex items-center gap-1">
                                                    <span className="material-symbols-outlined text-[14px]">health_and_safety</span>
                                                    <span className="font-semibold text-primary">Insurance:</span> <span className="truncate max-w-[200px]">{h.insurance_schemes}</span>
                                                </p>
                                            </div>
                                            <button className="text-primary font-bold text-sm flex items-center gap-2 group-hover:translate-x-1 transition-transform whitespace-nowrap">
                                                Open 3D Tour & Dossier
                                                <span className="material-symbols-outlined">arrow_forward</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Benchmarking Sidebar */}
                    <aside className="lg:col-span-4 space-y-8">
                        <div className="bg-primary text-on-primary p-10 rounded-xl sticky top-32">
                            <h4 className="font-headline text-2xl mb-2">Cost-to-Value <span className="serif-italic">Index</span></h4>
                            <p className="text-on-primary-container text-xs font-medium uppercase tracking-widest mb-10">Coimbatore Region</p>
                            
                            <div className="space-y-8">
                                {/* Dynamically Map Sidebar Bars from Data */}
                                {hospitals.map((bar, i) => {
                                    // Calculate relative width based on max price in array to make bars realistic
                                    const maxPriceInList = Math.max(...hospitals.map(h => h.min_price));
                                    const widthPercent = (bar.min_price / maxPriceInList) * 100;
                                    
                                    return (
                                        <div key={i} className="space-y-3">
                                            <div className="flex justify-between items-end">
                                                <span className="text-sm font-medium">{bar.name}</span>
                                                <span className="text-xs text-on-primary-container">{formatCurrency(bar.min_price)} Base</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-primary-container rounded-full overflow-hidden">
                                                <div className="h-full bg-secondary-fixed rounded-full" style={{width: `${widthPercent}%`}}></div>
                                            </div>
                                        </div>
                                    );
                                })}
                                
                                <div className="pt-8 border-t border-primary-container">
                                    <p className="text-xs text-on-primary-container leading-relaxed">
                                        Our AI Negotiator has secured an average of <strong>16% savings</strong> across these Coimbatore tier-1 facilities compared to standard walk-in rates.
                                    </p>
                                </div>
                            </div>
                            <button className="w-full mt-12 py-4 border border-on-primary-container text-on-primary text-xs font-bold uppercase tracking-widest hover:bg-primary-container transition-colors rounded">
                                Auto-Plan Flight & Visa
                            </button>
                        </div>
                    </aside>
                </div>
            </main>
            <Footer />
        </div>
    );
};