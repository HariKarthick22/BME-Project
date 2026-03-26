import React from "react";
import { Link, useNavigate } from "react-router-dom";

export const Navbar = () => {
  const navigate = useNavigate();

  return (
    <nav className="w-full bg-green-900 shadow-md border-b border-white/5">
      <div className="flex justify-between items-center px-12 py-6 w-full max-w-screen-2xl mx-auto">
        <Link
          to="/"
          className="font-headline text-2xl italic font-semibold text-white"
        >
          Mediorbit
        </Link>
        <div className="hidden md:flex space-x-8 items-center">
          <Link
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300"
            to="/search"
          >
            Destinations
          </Link>
          <a
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300"
            href="#"
          >
            Specialties
          </a>
          <a
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300"
            href="#"
          >
            Concierge
          </a>
          <a
            className="text-stone-300 font-medium hover:text-white transition-colors duration-300"
            href="#"
          >
            Journal
          </a>
        </div>
        <div className="flex items-center gap-6">
          <div
            className="hidden lg:flex items-center bg-[#363432] px-5 py-2.5 rounded-lg cursor-pointer hover:bg-[#2c2a28] transition-colors border border-white/5"
            onClick={() => navigate("/search")}
          >
            <span className="material-symbols-outlined text-stone-400 mr-2 text-[20px]">
              search
            </span>
            <span className="text-stone-400 text-sm font-medium">
              Search Dossier
            </span>
          </div>
          <button className="bg-[#004d36] text-white px-6 py-2.5 rounded-lg text-sm font-medium tracking-tight hover:bg-[#003827] transition-all">
            Consultation
          </button>
        </div>
      </div>
    </nav>
  );
};
