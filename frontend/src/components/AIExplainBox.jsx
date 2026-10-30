import React from 'react';
import { Sparkles, FileCode, CheckCircle2, Award, Cpu } from 'lucide-react';

export default function AIExplainBox({ ai }) {
  if (!ai) return null;

  const {
    summary = '',
    files_to_touch = [],
    skills_needed = [],
    first_steps = [],
    beginner_rating = 0,
    provider = 'gemini'
  } = ai;

  // Rating color helper
  const getRatingColor = (rating) => {
    if (rating >= 8) return '#10b981';
    if (rating >= 5) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="ai-explain-container">
      <div className="ai-explain-header">
        <div className="ai-header-left">
          <Sparkles size={16} />
          <span>AI Contribution Breakdown</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontWeight: 400 }}>
            ({provider})
          </span>
        </div>

        <div className="beginner-meter" title="Beginner Friendly Rating (10 = Easiest)">
          <Award size={14} color={getRatingColor(beginner_rating)} />
          <span>Beginner Rating:</span>
          <span className="meter-score" style={{ color: getRatingColor(beginner_rating) }}>
            {beginner_rating}/10
          </span>
        </div>
      </div>

      {/* Summary in Plain English */}
      <p className="ai-summary">{summary}</p>

      {/* Meta Grid: Files & Skills */}
      <div className="ai-meta-grid">
        {files_to_touch && files_to_touch.length > 0 && (
          <div className="ai-meta-section">
            <h5 style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <FileCode size={13} />
              <span>Files to Touch</span>
            </h5>
            <div className="ai-tag-list">
              {files_to_touch.map((f, idx) => (
                <span key={idx} className="code-pill">
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}

        {skills_needed && skills_needed.length > 0 && (
          <div className="ai-meta-section">
            <h5 style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <Cpu size={13} />
              <span>Skills Needed</span>
            </h5>
            <div className="ai-tag-list">
              {skills_needed.map((s, idx) => (
                <span key={idx} className="gh-label">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* First Steps */}
      {first_steps && first_steps.length > 0 && (
        <div className="ai-first-steps">
          <h5 style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <CheckCircle2 size={13} color="#10b981" />
            <span>Recommended First Steps</span>
          </h5>
          <ol className="steps-list">
            {first_steps.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
