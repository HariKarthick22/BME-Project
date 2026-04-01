import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion'; // <-- Import Framer Motion
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

// Animation Blueprints
const pageTransition = {
    initial: { opacity: 0, y: 15, scale: 0.99 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -15, scale: 0.99 },
    transition: { duration: 0.4, ease: "easeOut" }
};

const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.15 } // Delay between each card loading
    }
};

const cardVariants = {
    hidden: { opacity: 0, y: 40 },
    show: { 
        opacity: 1, 
        y: 0, 
        transition: { type: "spring", stiffness: 100, damping: 15 } 
    }
};

// This creates a beautiful, perfectly sized placeholder image directly in the browser's memory
const generateFallbackImage = (name) => {
    // We clean the name to avoid XML parsing errors if there are weird characters
    const cleanName = name.replace(/&/g, 'and'); 
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="100%" height="100%" fill="#e3e2e1"/><text x="50%" y="50%" font-family="sans-serif" font-weight="bold" font-size="24" fill="#006d36" text-anchor="middle" dominant-baseline="middle">${cleanName}</text></svg>`;
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

export const SearchResultsPage = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const [hospitals, setHospitals] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        if (location.state?.results) {
            setHospitals(location.state.results);
            setSearchQuery(location.state.query || 'Recommended Surgeries');
        } else {
            navigate('/'); 
        }
    }, [location, navigate]);

    const formatCurrency = (val) => {
        if (!val) return 'TBD';
        return `₹${(val / 100000).toFixed(1)}L`;
    };

    if (hospitals.length === 0) return (
        <div className="min-h-screen bg-surface flex flex-col items-center justify-center gap-6 px-12 text-center">
            <span className="material-symbols-outlined text-6xl text-outline">search_off</span>
            <h2 className="font-headline text-4xl text-primary italic">No matching hospitals found</h2>
            <p className="text-on-surface-variant max-w-md">Try a different condition or city — e.g. "knee replacement in Chennai" or "cardiac surgery Coimbatore".</p>
            <button onClick={() => navigate('/')} className="bg-primary text-on-primary px-8 py-3 rounded-xl font-medium hover:opacity-90 transition-opacity">
                Back to Search
            </button>
        </div>
    );

    return (
        // Wrap the entire page in motion.div for page transitions
        <motion.div 
            initial="initial" 
            animate="animate" 
            exit="exit" 
            variants={pageTransition}
            className="bg-surface"
        >
            <Navbar />
            <main className="pt-32 pb-24 px-12 max-w-screen-2xl mx-auto">
                <div className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-8">
                    <div className="space-y-2">
                        <p className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold flex items-center gap-2">
                            <span className="w-2 h-2 bg-secondary rounded-full animate-pulse"></span>
                            AI Swarm Analysis Complete
                        </p>
                        <h1 className="font-headline text-5xl md:text-6xl text-primary leading-none capitalize">
                            {searchQuery}
                        </h1>
                        <div className="flex items-center gap-3 mt-4">
                            <span className="bg-surface-container-high px-3 py-1 text-xs font-semibold rounded-full text-primary">NABH Accredited</span>
                            <span className="text-on-surface-variant text-sm border-l border-outline-variant pl-3">{hospitals.length} Validated Institutions Found</span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
                    {/* Wrap the cards list in a motion container to trigger the stagger effect */}
                    <motion.div 
                        variants={containerVariants} 
                        initial="hidden" 
                        animate="show" 
                        className="lg:col-span-8 space-y-8"
                    >
                        {hospitals.slice(0, 10).map((h) => (
                            // Each card gets the cardVariants animation
                            <motion.div 
                                variants={cardVariants}
                                key={h.id} 
                                onClick={() => navigate('/detail', { state: { hospital: h } })} 
                                className="group cursor-pointer relative bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_32px_rgba(26,28,28,0.04)] hover:shadow-[0_20px_48px_rgba(26,28,28,0.08)] transition-shadow duration-500 overflow-hidden"
                            >
                                <div className="flex flex-col md:flex-row gap-8">
                                    <div className="w-full md:w-56 h-auto min-h-[160px] bg-surface-container overflow-hidden rounded-lg">
                                        <img 
    alt={h.name} 
    loading="lazy" 
    decoding="async"
    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 bg-surface-variant" 
    src={h.image_url}
    onError={(e) => {
        e.currentTarget.onerror = null; // Prevent infinite loop
        // The browser instantly draws the SVG instead of asking a server!
        e.currentTarget.src = generateFallbackImage(h.name);
    }}
/>
                                    </div>
                                    
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
                                                        <span className="border border-outline-variant/30 text-on-surface-variant text-[10px] px-2 py-0.5 font-bold rounded uppercase">NABH</span>
                                                    )}
                                                    <span className="text-[10px] uppercase tracking-widest text-secondary font-bold ml-2">{h.category}</span>
                                                </div>
                                                <h3 className="font-headline text-3xl text-primary mb-2">{h.name}</h3>
                                                <p className="text-on-surface-variant text-sm flex items-center gap-1 leading-snug">
                                                    <span className="material-symbols-outlined text-sm">location_on</span>
                                                    <span className="max-w-[280px] truncate" title={h.address}>{h.city}, {h.state}</span>
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-4xl font-headline text-secondary leading-none">{((h.success_rate || 95) / 10).toFixed(1)}<span className="text-sm font-body text-on-surface-variant ml-1">/10</span></div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mt-1">AI Clinical Score</p>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 py-6 border-y border-outline-variant/10">
                                            <div>
                                                <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Success Rate</p>
                                                <p className="text-lg font-medium text-primary">{h.success_rate || '95'}%</p>
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

                                        <div className="mt-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                            <div className="flex flex-col gap-1">
                                                <p className="text-[11px] text-on-surface-variant flex items-center gap-1">
                                                    <span className="material-symbols-outlined text-[14px]">memory</span>
                                                    <span className="font-semibold text-primary truncate max-w-[300px]">Tech: {h.technology_stack}</span> 
                                                </p>
                                            </div>
                                            {/* Interactive Framer Motion Button */}
                                            <motion.button
                                                whileHover={{ scale: 1.05, x: 5 }}
                                                whileTap={{ scale: 0.95 }}
                                                onClick={(e) => { e.stopPropagation(); navigate('/detail', { state: { hospital: h } }); }}
                                                className="text-primary font-bold text-sm flex items-center gap-2 whitespace-nowrap bg-surface-container px-4 py-2 rounded hover:bg-surface-variant transition-colors"
                                            >
                                                Open Full Dossier
                                                <span className="material-symbols-outlined">arrow_forward</span>
                                            </motion.button>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>

                    {/* Benchmarking Sidebar */}
                    <aside className="lg:col-span-4 space-y-8">
                        <div className="bg-primary text-on-primary p-10 rounded-xl sticky top-32">
                            <h4 className="font-headline text-2xl mb-2">Cost-to-Value <span className="serif-italic">Index</span></h4>
                            <p className="text-on-primary-container text-xs font-medium uppercase tracking-widest mb-10">Market Analysis</p>
                            
                            <div className="space-y-8">
                                {hospitals.slice(0, 4).map((bar, i) => {
                                    const maxPriceInList = Math.max(...hospitals.map(h => h.min_price || 1));
                                    const widthPercent = ((bar.min_price || 1) / maxPriceInList) * 100;
                                    
                                    return (
                                        <div key={i} className="space-y-3">
                                            <div className="flex justify-between items-end">
                                                <span className="text-sm font-medium truncate max-w-[180px]">{bar.name}</span>
                                                <span className="text-xs text-on-primary-container">{formatCurrency(bar.min_price)} Base</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-primary-container rounded-full overflow-hidden">
                                                {/* Animate the progress bars filling up! */}
                                                <motion.div 
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${widthPercent}%` }}
                                                    transition={{ duration: 1.2, ease: "easeOut", delay: 0.5 }}
                                                    className="h-full bg-secondary-fixed rounded-full" 
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
            <Footer />
        </motion.div>
    );
};