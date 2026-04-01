import React from "react";
import { Link } from "react-router-dom";

export const Footer = () => (
  <footer className="w-full border-t border-stone-200/15 dark:border-stone-800/15 bg-[#faf9f8] dark:bg-stone-950">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-12 px-12 py-24 w-full max-w-screen-2xl mx-auto">
      <div className="md:col-span-1">
        <Link
          to="/"
          className="font-headline text-3xl italic text-emerald-950 dark:text-stone-100 mb-6 block"
        >
          Mediorbit
        </Link>
        <p className="text-stone-500 font-sans text-xs uppercase tracking-widest leading-loose">
          The premier global concierge for surgical excellence and clinical
          transparency.
        </p>
        <p className="font-sans text-[10px] uppercase tracking-widest text-stone-500 leading-relaxed mt-4">
          © 2024 Mediorbit. Managed Excellence.
        </p>
      </div>
      <div className="flex flex-col space-y-4">
        <span className="text-emerald-950 dark:text-emerald-500 font-sans text-xs uppercase tracking-widest font-bold mb-4">
          Legal Dossier
        </span>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Privacy Dossier
        </a>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Terms of Service
        </a>
      </div>
      <div className="flex flex-col space-y-4">
        <span className="text-emerald-950 dark:text-emerald-500 font-sans text-xs uppercase tracking-widest font-bold mb-4">
          Standards
        </span>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Clinical Standards
        </a>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Press
        </a>
      </div>
      <div className="flex flex-col space-y-4">
        <span className="text-emerald-950 dark:text-emerald-500 font-sans text-xs uppercase tracking-widest font-bold mb-4">
          Partnership
        </span>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Affiliates
        </a>
        <a
          className="text-stone-500 font-sans text-xs uppercase tracking-widest hover:text-emerald-700 underline-offset-4 underline transition-all"
          href="#"
        >
          Corporate Care
        </a>
      </div>
    </div>
  </footer>
);
