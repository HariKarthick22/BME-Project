import React from 'react';

export const HospitalCard = ({ name, location, score, successRate, recovery, waitTime, cost, advantage, badge, icon, image }) => (
  <div className="group relative bg-surface-container-lowest p-8 rounded-xl shadow-[0_12px_32px_rgba(26,28,28,0.04)] hover:shadow-[0_20px_48px_rgba(26,28,28,0.08)] transition-all duration-500 overflow-hidden">
    <div className="flex flex-col md:flex-row gap-8">
      <div className="w-full md:w-56 h-40 bg-surface-container overflow-hidden rounded-lg">
        <img className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" src={image} alt={name} />
      </div>
      <div className="flex-1">
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-secondary text-base" style={{ fontVariationSettings: "'FILL' 1" }}>{icon}</span>
              <span className="text-[10px] uppercase tracking-widest text-secondary font-bold">{badge}</span>
            </div>
            <h3 className="font-headline text-3xl text-primary mb-1">{name}</h3>
            <p className="text-on-surface-variant text-sm flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">location_on</span>{location}
            </p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-headline text-secondary leading-none">{score}<span className="text-sm font-body text-on-surface-variant ml-1">/10</span></div>
            <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mt-1">Clinical AI Score</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8 py-6 border-y border-outline-variant/10">
          {[
            { label: 'Success Rate', value: successRate, color: 'text-primary' },
            { label: 'Recovery', value: recovery, color: 'text-primary' },
            { label: 'Wait Time', value: waitTime, color: 'text-primary' },
            { label: 'Estimated Cost', value: cost, color: 'text-secondary' },
          ].map((stat, idx) => (
            <div key={idx}>
              <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">{stat.label}</p>
              <p className={`text-lg font-medium ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 flex items-center justify-between">
          <span className="bg-secondary/10 text-secondary text-[10px] px-2 py-0.5 font-bold rounded uppercase">Market Advantage: {advantage}</span>
          <button className="text-primary font-bold text-sm flex items-center gap-2 group-hover:translate-x-1 transition-transform">
            View Full Dossier <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  </div>
);