import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ScrollToTop } from './components/ScrollToTop';
import { LandingPage } from './pages/LandingPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { HospitalDetailPage } from './pages/HospitalDetailPage';

function App() {
    return (
        <BrowserRouter>
            <ScrollToTop />
            <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/search" element={<SearchResultsPage />} />
                <Route path="/detail" element={<HospitalDetailPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;