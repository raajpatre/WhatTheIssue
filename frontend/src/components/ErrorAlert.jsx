import React from 'react';
import { AlertCircle, Clock, ShieldAlert, WifiOff, RotateCcw } from 'lucide-react';

export default function ErrorAlert({ error, onRetry }) {
  if (!error) return null;

  const code = error.code || 'UNKNOWN_ERROR';
  const rawMessage = error.message || 'An unexpected error occurred.';

  // Friendly error mapping according to D2 quality specs
  let friendlyTitle = 'Unable to Complete Request';
  let friendlyDesc = rawMessage;
  let icon = <AlertCircle size={20} color="#f0a190" />;

  switch (code) {
    case 'RATE_LIMITED':
      friendlyTitle = 'GitHub Rate Limit Reached';
      friendlyDesc = 'GitHub API rate limit hit. Please try again in a minute, or configure a read-only GITHUB_TOKEN on the backend.';
      icon = <Clock size={20} color="#f2bf72" />;
      break;

    case 'INVALID_REPO':
      friendlyTitle = 'Invalid Repository Format';
      friendlyDesc = 'Please enter a valid GitHub URL or slug in the format "owner/repo" (e.g., pallets/flask or fastapi/fastapi).';
      icon = <ShieldAlert size={20} color="#f0a190" />;
      break;

    case 'REPO_NOT_FOUND':
      friendlyTitle = 'Repository Not Found';
      friendlyDesc = 'This repository could not be located on GitHub. Check the spelling or confirm that the repository is public.';
      icon = <AlertCircle size={20} color="#f0a190" />;
      break;

    case 'NETWORK_ERROR':
      friendlyTitle = 'Connection Failed';
      friendlyDesc = 'Could not reach the backend service. Check if your FastAPI server is running on localhost:8000 or enable VITE_USE_MOCK=1 in .env for mock testing.';
      icon = <WifiOff size={20} color="#f0a190" />;
      break;

    default:
      friendlyTitle = 'Analysis Failed';
      friendlyDesc = rawMessage;
  }

  return (
    <div className="alert-banner error" style={{ flexDirection: 'column', gap: '0.75rem', padding: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
        {icon}
        <strong style={{ fontSize: '1rem', color: '#fecaca' }}>{friendlyTitle}</strong>
      </div>

      <p style={{ margin: 0, fontSize: '0.875rem', color: '#fca5a5', lineHeight: 1.5 }}>
        {friendlyDesc}
      </p>

      {onRetry && (
        <div style={{ marginTop: '0.25rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onRetry}
            style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}
          >
            <RotateCcw size={13} />
            <span>Try Again</span>
          </button>
        </div>
      )}
    </div>
  );
}
