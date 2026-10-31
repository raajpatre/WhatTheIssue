import React from 'react';
import { ExternalLink, Bell, FolderGit2, RefreshCw } from 'lucide-react';

export default function ResultsHeader({ repo, issues = [], onTrackRepo, onRefresh }) {
  const safeCount = issues.filter((i) => i.status === 'safe').length;
  const claimedCount = issues.filter((i) => i.status === 'claimed').length;
  const staleCount = issues.filter((i) => i.status === 'stale').length;
  const unclearCount = issues.filter((i) => i.status === 'unclear').length;

  return (
    <div className="results-header-bar">
      <div className="repo-meta">
        <div className="repo-avatar">
          <FolderGit2 size={24} />
        </div>
        <div>
          <div className="repo-title-row">
            <h2 className="repo-name-text">{repo}</h2>
            <a
              href={`https://github.com/${repo}`}
              target="_blank"
              rel="noopener noreferrer"
              className="external-link"
              title="View on GitHub"
            >
              <ExternalLink size={16} />
            </a>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            <span>
              <strong style={{ color: '#9bd3ac' }}>{safeCount}</strong> safe to start
            </span>
            <span>·</span>
            <span>{issues.length} total analyzed</span>
          </div>
        </div>
      </div>

      <div className="results-actions">
        {onRefresh && (
          <button
            className="btn btn-secondary"
            onClick={onRefresh}
            title="Re-run analysis"
            style={{ padding: '0.55rem 0.85rem' }}
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
        )}

        <button
          className="btn btn-primary"
          onClick={onTrackRepo}
          style={{ padding: '0.55rem 1.15rem' }}
        >
          <Bell size={16} />
          <span>Track in Telegram</span>
        </button>
      </div>
    </div>
  );
}
