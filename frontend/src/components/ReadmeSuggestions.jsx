import React from 'react';
import { BookOpen, Sparkles, FileText, CheckCircle } from 'lucide-react';

export default function ReadmeSuggestions({ suggestions = [], repo }) {
  if (!suggestions || suggestions.length === 0) {
    return (
      <div className="search-card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
        <BookOpen size={36} color="var(--text-subtle)" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>No README suggestions available</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          We could not find starter opportunities in this repository's README.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '1.25rem' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
          When labelled issues are scarce or claimed, these beginner opportunities were identified directly from the repository&apos;s documentation:
        </p>
      </div>

      <div className="suggestions-grid">
        {suggestions.map((item, idx) => (
          <div key={idx} className="suggestion-card">
            <span className="suggestion-area-badge">
              {item.area || 'docs'}
            </span>

            <h3 className="suggestion-title">{item.title}</h3>
            <p className="suggestion-desc">{item.description}</p>

            {item.why_beginner_friendly && (
              <div className="suggestion-why">
                <strong style={{ display: 'block', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                  Why this is beginner friendly:
                </strong>
                <span>{item.why_beginner_friendly}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
