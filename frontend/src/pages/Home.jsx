import React from 'react';

export const Home = () => (
  <div className="pt-12">
    <section className="relative min-h-[80vh] flex flex-col items-center justify-center px-12 text-center">
      <span className="font-sans text-xs uppercase tracking-[0.3em] text-on-surface-variant mb-8 block">Global Surgical Network</span>
      <h1 className="font-headline text-7xl md:text-8xl text-primary leading-[1.1] mb-12 italic">
        Find and book the world's <br/>best surgeries, <span className="text-secondary">instantly.</span>
      </h1>
      <div className="max-w-3xl mx-auto bg-surface-container-lowest p-2 rounded-2xl shadow-sm border border-outline-variant/10 flex flex-col md:flex-row items-center gap-2">
        <div className="flex-1 flex items-center px-6 py-4 w-full">
          <span className="material-symbols-outlined text-outline mr-3">clinical_notes</span>
          <input className="bg-transparent border-none outline-none w-full font-body text-lg placeholder:text-outline-variant" placeholder="Describe your procedure or condition..." type="text" />
        </div>
        <button className="w-full md:w-auto bg-primary text-on-primary px-10 py-4 rounded-xl font-medium">Analyze</button>
      </div>
    </section>

    <section className="bg-surface-container-low py-24 px-12 grid grid-cols-1 md:grid-cols-3 gap-16 text-center rounded-3xl mb-24">
       <div>
         <span className="font-headline text-8xl text-primary italic">140+</span>
         <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant mt-4">Global Partner Hospitals</p>
       </div>
       <div>
         <span className="font-headline text-8xl text-primary italic">30%</span>
         <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant mt-4">Avg. Clinical Savings</p>
       </div>
       <div>
         <span className="font-headline text-8xl text-primary italic">98.2%</span>
         <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant mt-4">Surgical Success Rating</p>
       </div>
    </section>
  </div>
);