import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const HospitalDetailPage = () => {
    const location = useLocation();
    const navigate = useNavigate();
    
    // Extract the hospital data passed from the search page
    const hospital = location.state?.hospital;

    // Safety check: If someone navigates directly to /detail without clicking a card, send them back
    useEffect(() => {
        if (!hospital) {
            navigate('/search');
        }
    }, [hospital, navigate]);

    if (!hospital) return null; // Prevents render errors while redirecting

    // Helper to format currency dynamically
    const formatCurrency = (val) => `₹${(val / 100000).toFixed(1)}L`;

    return (
        <div className="bg-surface">
            <Navbar />
            <main className="pt-32 pb-24">
                {/* Hero Section */}
                <section className="px-12 max-w-screen-2xl mx-auto mb-20">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-end">
                        <div className="lg:col-span-8">
                            <div className="flex items-center gap-4 mb-6">
                                <span className="bg-secondary-container text-on-secondary-container px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold rounded">Clinical Excellence</span>
                                <div className="flex gap-2">
                                    {hospital.jci_accredited === 'Yes' && (
                                        <span className="text-xs font-semibold px-2 py-1 border border-secondary text-secondary rounded uppercase">JCI Accredited</span>
                                    )}
                                    {hospital.nabh_accredited === 'Yes' && (
                                        <span className="text-xs font-semibold px-2 py-1 border border-outline-variant/30 rounded uppercase">NABH Certified</span>
                                    )}
                                </div>
                            </div>
                            <h1 className="font-headline text-7xl md:text-8xl italic text-primary leading-tight mb-8">
                                {hospital.name.split(' ').slice(0, -1).join(' ')}<br/>
                                <span className="text-5xl">{hospital.name.split(' ').slice(-1)}</span>
                            </h1>
                            <p className="text-on-surface-variant text-xl max-w-2xl leading-relaxed flex items-center gap-2">
                                <span className="material-symbols-outlined text-xl">location_on</span>
                                {hospital.address}
                            </p>
                        </div>
                        <div className="lg:col-span-4 flex flex-col items-end">
                            <div className="bg-primary p-10 rounded-xl text-center w-full max-w-[280px] shadow-xl relative overflow-hidden group">
                                <div className="absolute inset-0 bg-gradient-to-br from-primary to-secondary/20 opacity-50"></div>
                                <div className="relative z-10">
                                    <div className="text-secondary-fixed text-sm uppercase tracking-widest mb-2">MediOrbit AI Score</div>
                                    <div className="font-headline text-6xl text-on-primary italic mb-2">{(hospital.success_rate / 10).toFixed(1)}</div>
                                    <div className="h-1 w-16 bg-secondary mx-auto mb-4"></div>
                                    <p className="text-on-primary/60 text-[10px] leading-tight uppercase tracking-tighter">Superior Clinical Outcome Index</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* High-Impact Stats Bento Grid */}
                <section className="px-12 max-w-screen-2xl mx-auto mb-24">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="bg-surface-container-lowest p-12 rounded-xl shadow-[0_12px_32px_rgba(26,28,28,0.06)] flex flex-col justify-between h-64 border-l-4 border-secondary">
                            <span className="material-symbols-outlined text-4xl text-secondary">verified</span>
                            <div>
                                <div className="font-headline text-5xl text-primary mb-1">{hospital.success_rate}%</div>
                                <div className="text-on-surface-variant uppercase tracking-widest text-xs">Clinical Success Rate</div>
                            </div>
                        </div>
                        <div className="bg-surface-container-lowest p-12 rounded-xl shadow-[0_12px_32px_rgba(26,28,28,0.06)] flex flex-col justify-between h-64">
                            <span className="material-symbols-outlined text-4xl text-primary">local_hospital</span>
                            <div>
                                <div className="font-headline text-3xl text-primary mb-2 leading-tight">{hospital.technology_stack.split(',')[0]}</div>
                                <div className="text-on-surface-variant uppercase tracking-widest text-xs">Primary Technology</div>
                            </div>
                        </div>
                        <div className="bg-surface-container-lowest p-12 rounded-xl shadow-[0_12px_32px_rgba(26,28,28,0.06)] flex flex-col justify-between h-64">
                            <span className="material-symbols-outlined text-4xl text-primary">stethoscope</span>
                            <div>
                                <div className="font-headline text-4xl text-primary mb-2">{hospital.lead_doctors.split(',')[0]}</div>
                                <div className="text-on-surface-variant uppercase tracking-widest text-xs">Lead Surgeon ({hospital.lead_doctor_experience})</div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Treatment Timeline & Cost Breakdown */}
                <section className="px-12 max-w-screen-2xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-16">
                    <div className="lg:col-span-7">
                        <div className="mb-12">
                            <h2 className="font-headline text-4xl italic text-primary mb-4">Your "Jolly Holidays" Timeline</h2>
                            <p className="text-on-surface-variant">A curated recovery path tailored for your stay at {hospital.name}.</p>
                        </div>
                        <div className="space-y-0 border-l border-outline-variant/30 ml-4">
                            <div className="relative pl-12 pb-12">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-stone-300"></div>
                                <span className="font-headline text-2xl text-primary block mb-2">Arrival: Airport to Hotel</span>
                                <p className="text-on-surface-variant text-sm leading-relaxed">VIP transit picks you up from Coimbatore International Airport. Settle into your premium recovery hotel.</p>
                            </div>
                            <div className="relative pl-12 pb-12">
                                <div className="absolute -left-[13px] -top-1 w-6 h-6 rounded-full bg-secondary ring-4 ring-secondary-container"></div>
                                <div className="bg-surface-container-low p-8 rounded-xl">
                                    <span className="font-headline text-3xl text-secondary italic block mb-3">Surgery: {hospital.category} Intervention</span>
                                    <p className="text-primary font-medium mb-4">Minimally invasive procedure utilizing {hospital.technology_stack}.</p>
                                    <div className="flex items-center gap-4">
                                        <span className="bg-white px-3 py-1 rounded text-[10px] font-bold text-primary">PRECISION FOCUS</span>
                                        <span className="bg-white px-3 py-1 rounded text-[10px] font-bold text-primary">ICU MONITORING</span>
                                    </div>
                                </div>
                            </div>
                            <div className="relative pl-12 pb-12">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-stone-300"></div>
                                <span className="font-headline text-2xl text-primary block mb-2">Recovery: {hospital.avg_length_of_stay.split(',')[0]}</span>
                                <p className="text-on-surface-variant text-sm leading-relaxed">Personalized physiotherapy begins under the care of {hospital.lead_doctors.split(',')[0]}'s team.</p>
                            </div>
                            <div className="relative pl-12">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-stone-300"></div>
                                <span className="font-headline text-2xl text-primary block mb-2">Therapeutic Rest: {hospital.avg_length_of_stay.split(',')[1]}</span>
                                <p className="text-on-surface-variant text-sm leading-relaxed">Transfer back to your luxury hotel. Enjoy concierge-guided local experiences in Coimbatore before international travel clearance.</p>
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-5">
                        <div className="bg-surface-container-high rounded-2xl p-10 sticky top-32 shadow-sm">
                            <h3 className="font-headline text-3xl italic text-primary mb-8 text-center">Cost Estimate Dossier</h3>
                            <div className="space-y-6 mb-10">
                                {[
                                    { label: 'Surgical & Facility Fee', cost: formatCurrency(hospital.min_price * 0.7) },
                                    { label: 'Diagnostics & Labs', cost: formatCurrency(hospital.min_price * 0.15) },
                                    { label: 'Anesthesia & OT Charges', cost: formatCurrency(hospital.min_price * 0.15) }
                                ].map((item, i) => (
                                    <div key={i} className="flex justify-between items-center pb-4 border-b border-outline-variant/20">
                                        <span className="text-on-surface-variant text-sm uppercase tracking-wider">{item.label}</span>
                                        <span className="font-headline text-xl text-primary">{item.cost}</span>
                                    </div>
                                ))}
                                <div className="flex justify-between items-center pt-4 border-b-2 border-primary pb-4">
                                    <span className="text-primary font-bold uppercase tracking-widest text-xs">Est. Base Investment</span>
                                    <span className="font-headline text-4xl text-secondary">{formatCurrency(hospital.min_price)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-on-surface-variant text-xs uppercase tracking-wider font-semibold">Complex Case Maximum</span>
                                    <span className="font-headline text-lg text-outline">{formatCurrency(hospital.max_price)}</span>
                                </div>
                            </div>
                            <div className="bg-surface-container-lowest p-6 rounded-lg mb-8">
                                <div className="flex gap-4 items-start">
                                    <span className="material-symbols-outlined text-secondary">info</span>
                                    <div className="text-[11px] leading-relaxed text-on-surface-variant uppercase">
                                        <span className="font-bold block mb-1 text-primary">Accepted Schemes:</span>
                                        {hospital.insurance_schemes}
                                    </div>
                                </div>
                            </div>
                            <button className="w-full bg-primary text-on-primary py-5 rounded-lg font-bold tracking-[0.1em] text-xs uppercase hover:bg-primary-container transition-all">
                                Generate Official Visa Invite
                            </button>
                        </div>
                    </div>
                </section>

                {/* Hero Image / Vibe Section */}
                <section className="mt-32 px-12 max-w-screen-2xl mx-auto">
                    <div className="relative h-[600px] rounded-3xl overflow-hidden group">
                        <img alt={`${hospital.name} Interior`} className="w-full h-full object-cover grayscale-[0.2] transition-transform duration-700 group-hover:scale-105" src={hospital.img}/>
                        <div className="absolute inset-0 bg-gradient-to-t from-primary/90 via-primary/20 to-transparent"></div>
                        <div className="absolute bottom-16 left-16 max-w-2xl">
                            <h2 className="font-headline text-5xl text-on-primary italic mb-6">The Precision Pulse of {hospital.name.split(' ')[0]}</h2>
                            <p className="text-on-primary/80 text-lg leading-relaxed mb-8">
                                "In medicine, the difference between a good outcome and a perfect one is measured in millimeters. With our {hospital.technology_stack.split(',')[0]}, those millimeters are our obsession."
                            </p>
                            <div className="flex items-center gap-4 text-on-primary font-headline italic text-xl">
                                — {hospital.lead_doctors.split(',')[0]}
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
};