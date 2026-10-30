import React, { useState } from 'react';
import { ExternalLink, Sparkles, Check, AlertTriangle, AlertCircle, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
import AIExplainBox from './AIExplainBox';
import { explainIssue } from '../api';

export default function IssueCard({ scoredIssue, repo }) {
  const { issue, score, status, reasons = [], ai: initialAi } = scoredIssue;
  
  // State for AI insight and lazy loading
  const [aiInsight, setAiInsight] = useState(initialAi || null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [isExplainOpen, setIsExplainOpen] = useState(Boolean(initialAi));
  const [explainError, setExplainError] = useState(null);

  // Status badge config
  const statusConfig = {
    safe: {
      label: 'Safe to Start',
      className: 'safe',
      icon: <Check size={13} strokeWidth={2.5} />
    },
    claimed: {
      label: 'Claimed / In-Progress',
      className: 'claimed',
      icon: <AlertTriangle size={13} strokeWidth={2.5} />
    },
    stale: {
      label: 'Stale / Inactive',
      className: 'stale',
      icon: <AlertCircle size={13} strokeWidth={2.5} />
    },
    unclear: {
      label: 'Needs Context',
      className: 'unclear',
      icon: <HelpCircle size={13} strokeWidth={2.5} />
    }
  };

  const currentStatus = statusConfig[status] || statusConfig.unclear;

  // Lazy trigger for AI Explain
  const handleToggleExplain = async () => {
    if (isExplainOpen) {
      setIsExplainOpen(false);
      return;
    }

    setIsExplainOpen(true);

    // If already cached in state, don't refetch!
    if (aiInsight) {
      return;
    }

    setIsExplaining(true);
    setExplainError(null);

    try {
      const data = await explainIssue(repo || issue.repo, issue.number);
      setAiInsight(data);
    } catch (err) {
      setExplainError(err.message || 'Failed to generate explanation. Please try again.');
    } finally {
      setIsExplaining(false);
    }
  };

  return (
    <article className="issue-card" id={`issue-${issue.number}`}>
      <div className="issue-card-top">
        <div className="issue-title-group">
          <span className="issue-number-tag">#{issue.number}</span>
          <a
            href={issue.url}
            target="_blank"
            rel="noopener noreferrer"
            className="issue-title-link"
            title="Open issue on GitHub"
          >
            {issue.title}
            <ExternalLink size={13} style={{ display: 'inline', marginLeft: '6px', opacity: 0.7 }} />
          </a>
        </div>

        <div className={`status-badge ${currentStatus.className}`}>
          {currentStatus.icon}
          <span>{currentStatus.label}</span>
        </div>
      </div>

      {/* Score Progress Bar */}
      <div className="score-row">
        <span className="score-label">Safety Score</span>
        <div className="score-bar-track">
          <div
            className={`score-bar-fill ${currentStatus.className}`}
            style={{ width: `${Math.max(5, Math.min(100, score))}%` }}
          />
        </div>
        <span className="score-val" style={{ color: score >= 70 ? '#34d399' : score >= 40 ? '#fbbf24' : '#f87171' }}>
          {score}/100
        </span>
      </div>

      {/* Reasons Why */}
      {reasons && reasons.length > 0 && (
        <ul className="reasons-list">
          {reasons.map((reason, idx) => (
            <li key={idx} className="reason-item">
              <span className="reason-bullet">•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      )}

      {/* GitHub Labels */}
      {issue.labels && issue.labels.length > 0 && (
        <div className="issue-labels">
          {issue.labels.map((label, idx) => (
            <span key={idx} className="gh-label">
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Explain Button */}
      <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleToggleExplain}
          disabled={isExplaining}
          style={{ fontSize: '0.8125rem', padding: '0.4rem 0.85rem' }}
        >
          <Sparkles size={14} color="#a855f7" />
          <span>
            {isExplaining
              ? 'Consulting AI...'
              : isExplainOpen
              ? 'Hide Breakdown'
              : 'Explain this issue'}
          </span>
          {isExplainOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {issue.linked_pr_open && (
          <span style={{ fontSize: '0.75rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <AlertTriangle size={12} /> Open PR detected
          </span>
        )}
      </div>

      {/* AI Breakdown Drawer */}
      {isExplainOpen && (
        <>
          {explainError ? (
            <div className="alert-banner error" style={{ marginTop: '1rem', padding: '0.75rem 1rem' }}>
              <span>{explainError}</span>
            </div>
          ) : isExplaining ? (
            <div className="ai-explain-container" style={{ textAlign: 'center', padding: '1.5rem' }}>
              <div className="skeleton skeleton-title" style={{ width: '40%', margin: '0 auto 1rem' }} />
              <div className="skeleton skeleton-text" style={{ width: '80%', margin: '0 auto 0.5rem' }} />
              <div className="skeleton skeleton-short" style={{ width: '60%', margin: '0 auto' }} />
            </div>
          ) : (
            <AIExplainBox ai={aiInsight} />
          )}
        </>
      )}
    </article>
  );
}
