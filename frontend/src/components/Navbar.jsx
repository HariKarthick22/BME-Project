import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchHospitalsData, analyzeQuery } from "../utils/dummyAI";

export const Navbar = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const browseAll = async (query = "top hospitals Tamil Nadu") => {
    if (loading) return;
    setLoading(true);
    try {
      const all = await fetchHospitalsData();
      const results = analyzeQuery(query, all);
      navigate("/search", { state: { query, results } });
    } catch {
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  const openChat = () => {
    // Dispatch a custom event — ChatWidget listens for this to open itself
    window.dispatchEvent(new CustomEvent("carepath:open-chat"));
  };

  return (
    <nav className="w-full bg-primary shadow-md border-b border-white/5">
      <div className="flex justify-between items-center px-12 py-6 w-full max-w-screen-2xl mx-auto">
        <Link to="/" className="font-headline text-2xl italic font-semibold text-white">
          Mediorbit
        </Link>
        <div className="hidden md:flex space-x-8 items-center">
          <button
            onClick={() => browseAll("top hospitals Tamil Nadu")}
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? "Loading…" : "Destinations"}
          </button>
          <button onClick={() => browseAll("cardiac surgery Chennai")}
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300">
            Specialties
          </button>
          <button onClick={openChat}
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300">
            Concierge
          </button>
          <button onClick={openChat}
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300">
            Journal
          </button>
        </div>
        <div className="flex items-center gap-6">
          <div
            onClick={() => browseAll("top hospitals Tamil Nadu")}
            className="hidden lg:flex items-center bg-[#363432] px-5 py-2.5 rounded-lg cursor-pointer hover:bg-[#2c2a28] transition-colors border border-white/5"
          >
            <span className="material-symbols-outlined text-stone-400 mr-2 text-[20px]">
              {loading ? "progress_activity" : "search"}
            </span>
            <span className="text-stone-400 text-sm font-medium">Search Dossier</span>
          </div>
          <button
            onClick={openChat}
            className="bg-[#004d36] text-white px-6 py-2.5 rounded-lg text-sm font-medium tracking-tight hover:bg-[#003827] transition-all flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[16px]" style={{fontVariationSettings:"'FILL' 1"}}>chat</span>
            Consultation
          </button>
        </div>
      </div>
    </nav>
  );
};
