import React from 'react';
import { GitPullRequest, Radio, Bell, ArrowLeft } from 'lucide-react';

export default function Header({ currentView, setCurrentView, currentRepo, onResetSearch }) {
  const isMock = import.meta.env.VITE_USE_MOCK !== '0' && import.meta.env.VITE_USE_MOCK !== 'false';

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div 
          className="brand" 
          onClick={onResetSearch} 
          role="button" 
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onResetSearch(); }}
          title="Return to Home"
        >
          <div className="brand-icon">
            <GitPullRequest size={18} strokeWidth={2.5} />
          </div>
          <span className="brand-name">
            my<span>OpenSource</span>
          </span>
        </div>

        <div className="nav-actions">
          <div className={`badge-mode ${isMock ? 'mock' : 'live'}`} title={isMock ? 'Running on Mock Data (VITE_USE_MOCK=1)' : 'Connected to FastAPI Backend'}>
            <span className="dot"></span>
            <span>{isMock ? 'Mock Mode' : 'Backend Live'}</span>
          </div>

          {currentView !== 'home' && (
            <button 
              className="btn btn-secondary" 
              onClick={onResetSearch}
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8125rem' }}
            >
              <ArrowLeft size={15} />
              <span>New Search</span>
            </button>
          )}

          <button 
            className={`btn ${currentView === 'track' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCurrentView(currentView === 'track' ? (currentRepo ? 'results' : 'home') : 'track')}
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.8125rem' }}
          >
            <Bell size={15} />
            <span>Track Repos</span>
          </button>
        </div>
      </div>
    </header>
  );
}
