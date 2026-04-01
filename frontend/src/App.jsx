import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { ScrollToTop } from './components/ScrollToTop';
import { LandingPage } from './pages/LandingPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { HospitalDetailPage } from './pages/HospitalDetailPage';
import { ChatWidget } from './components/ChatWidget';

// We extract the routes into a sub-component so useLocation() works
const AnimatedRoutes = () => {
    const location = useLocation();
    
    return (
        // mode="wait" tells the old page to fade out completely BEFORE the new page fades in
        <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/search" element={<SearchResultsPage />} />
                <Route path="/detail" element={<HospitalDetailPage />} />
            </Routes>
        </AnimatePresence>
    );
};

function App() {
    return (
        <BrowserRouter>
            <ScrollToTop />
            <AnimatedRoutes />
            <ChatWidget />
        </BrowserRouter>
    );
}

export default App;