import React from 'react';

export default function SkeletonLoader({ count = 3 }) {
  return (
    <div className="issues-stack">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="issue-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div className="skeleton skeleton-title" style={{ width: '55%' }} />
            <div className="skeleton" style={{ width: '110px', height: '26px', borderRadius: '9999px' }} />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <div className="skeleton" style={{ width: '100%', height: '6px', borderRadius: '9999px' }} />
          </div>

          <div className="skeleton skeleton-text" style={{ width: '85%' }} />
          <div className="skeleton skeleton-text" style={{ width: '70%' }} />

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <div className="skeleton" style={{ width: '120px', height: '24px', borderRadius: '4px' }} />
            <div className="skeleton" style={{ width: '90px', height: '24px', borderRadius: '4px' }} />
          </div>
        </div>
      ))}
    </div>
  );
}
