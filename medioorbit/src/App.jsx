import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './styles/globals.css';
import './styles/animations.css';
import HomePage from './ui/pages/HomePage';
import ResultsPage from './ui/pages/ResultsPage';
import HospitalDetailPage from './ui/pages/HospitalDetailPage';
import { NavigationProvider } from './context/NavigationAgent';
import ChatWidget from './ui/components/ChatWidget';
import MedicalDocScanner from './ui/components/MedicalDocScanner';
import MediOrbitChatbot from './ui/components/MediOrbitChatbot';

export default function App() {
  return (
    <NavigationProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/hospital/:id" element={<HospitalDetailPage />} />
        </Routes>
        <MediOrbitChatbot />
      </BrowserRouter>
    </NavigationProvider>
  );
}