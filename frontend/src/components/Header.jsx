import React from 'react';
import { Bell, ArrowLeft } from 'lucide-react';

export default function Header({ currentView, setCurrentView, currentRepo, onResetSearch }) {
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
          <img
            className="brand-logo"
            src="/brand/myopensource-logo.png"
            alt="myOpenSource"
          />
        </div>

        <div className="nav-actions">

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
