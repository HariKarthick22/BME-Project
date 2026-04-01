import React from "react";

export const NavBar = () => (
  <nav className="fixed top-0 w-full z-50 bg-[#faf9f8]/80 backdrop-blur-xl shadow-[0_12px_32px_rgba(26,28,28,0.06)]">
    <div className="flex justify-between items-center px-12 py-6 w-full max-w-screen-2xl mx-auto">
      <div className="font-headline text-2xl italic font-semibold text-primary">
        Mediorbit
      </div>
      <div className="hidden md:flex items-center space-x-12">
        {["Destinations", "Specialties", "Concierge", "Journal"].map((item) => (
          <a
            key={item}
            className="text-stone-600 font-medium hover:text-primary transition-colors duration-300"
            href="#"
          >
            {item}
          </a>
        ))}
      </div>
      <div className="flex items-center gap-6">
        <button className="bg-gradient-to-br from-primary to-primary-container text-on-primary px-8 py-3 rounded-lg font-medium hover:opacity-90 transition-all">
          Consultation
        </button>
      </div>
    </div>
  </nav>
);

export const Footer = () => (
  <footer className="bg-[#faf9f8] border-t border-stone-200/15">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-12 px-12 py-24 w-full max-w-screen-2xl mx-auto">
      <div className="md:col-span-1">
        <div className="font-headline text-3xl italic text-primary mb-6">
          Mediorbit
        </div>
        <p className="text-xs uppercase tracking-widest text-stone-500 leading-relaxed">
          © 2024 The Clinical Editorial.
          <br />
          Managed Excellence.
        </p>
      </div>
    </div>
  </footer>
);

export const Layout = ({ children }) => (
  <>
    <NavBar />
    <main className="pt-32 pb-24 px-12 max-w-screen-2xl mx-auto">
      {children}
    </main>
    <Footer />
  </>
);
