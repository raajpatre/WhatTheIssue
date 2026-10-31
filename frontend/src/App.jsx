import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import HomeHero from './components/HomeHero';
import ResultsHeader from './components/ResultsHeader';
import IssueCard from './components/IssueCard';
import ReadmeSuggestions from './components/ReadmeSuggestions';
import TrackView from './components/TrackView';
import SkeletonLoader from './components/SkeletonLoader';
import ErrorAlert from './components/ErrorAlert';
import { analyzeRepo, getSuggestions } from './api';
import { Info, Sparkles, Filter, BookOpen, Layers } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState('home'); // 'home' | 'results' | 'track'
  const [activeTab, setActiveTab] = useState('issues'); // 'issues' | 'readme'

  const [currentRepo, setCurrentRepo] = useState('');
  const [appliedTags, setAppliedTags] = useState(['good first issue']);
  const [issues, setIssues] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [note, setNote] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filter toggle: by default show safe and unclear; toggle shows claimed and stale too
  const [showAllIssues, setShowAllIssues] = useState(false);

  // Toast feedback state
  const [toasts, setToasts] = useState([]);

  const addToast = (message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  };

  const handleAnalyze = async (repoUrl, tags) => {
    setLoading(true);
    setError(null);
    setNote(null);
    setIssues([]);
    setSuggestions([]);

    try {
      const data = await analyzeRepo(repoUrl, tags);
      setCurrentRepo(data.repo);
      setAppliedTags(tags);
      setIssues(data.issues || []);
      setNote(data.note || null);

      // Lazily fetch suggestions from README as well
      getSuggestions(data.repo)
        .then((suggs) => setSuggestions(suggs || []))
        .catch((err) => console.warn('Could not load suggestions', err));

      // If note is present or issues empty, switch to README tab as required by D1 spec
      if (data.note || (data.issues && data.issues.length === 0)) {
        setActiveTab('readme');
      } else {
        setActiveTab('issues');
      }

      setCurrentView('results');
    } catch (err) {
      setError(err);
      setCurrentView('home');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSearch = () => {
    setCurrentView('home');
    setError(null);
  };

  // Filtered issues based on toggle
  const visibleIssues = issues.filter((item) => {
    if (showAllIssues) return true;
    return item.status === 'safe' || item.status === 'unclear';
  });

  const hiddenCount = issues.length - visibleIssues.length;

  return (
    <div className="app-container">
      <Header
        currentView={currentView}
        setCurrentView={setCurrentView}
        currentRepo={currentRepo}
        onResetSearch={handleResetSearch}
      />

      <main className="main-content">
        {/* Error notification if returned while searching */}
        {error && (
          <div style={{ maxWidth: '840px', margin: '0 auto 1.5rem' }}>
            <ErrorAlert error={error} onRetry={() => error && handleAnalyze(currentRepo || 'pallets/flask', appliedTags)} />
          </div>
        )}

        {/* Home Screen */}
        {currentView === 'home' && (
          <>
            {loading ? (
              <div style={{ maxWidth: '840px', margin: '3rem auto 0' }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                  <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Analyzing GitHub Repository...</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    Scanning pull requests, issue activity, and maintainer comments.
                  </p>
                </div>
                <SkeletonLoader count={3} />
              </div>
            ) : (
              <HomeHero onAnalyze={handleAnalyze} loading={loading} />
            )}
          </>
        )}

        {/* Results Screen */}
        {currentView === 'results' && (
          <div className="results-view">
            <ResultsHeader
              repo={currentRepo}
              issues={issues}
              onTrackRepo={() => setCurrentView('track')}
              onRefresh={() => handleAnalyze(currentRepo, appliedTags)}
            />

            {/* Note banner if repo issues were empty or had specific note */}
            {note && (
              <div className="alert-banner info">
                <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <strong>Maintainer Note:</strong>
                  <p style={{ marginTop: '0.25rem', color: 'var(--muted)' }}>{note}</p>
                </div>
              </div>
            )}

            {/* Tabs Navigation */}
            <div className="tabs-nav">
              <button
                type="button"
                className={`tab-btn ${activeTab === 'issues' ? 'active' : ''}`}
                onClick={() => setActiveTab('issues')}
              >
                <Layers size={16} />
                <span>Issues</span>
                <span className="tab-counter">{issues.length}</span>
              </button>

              <button
                type="button"
                className={`tab-btn ${activeTab === 'readme' ? 'active' : ''}`}
                onClick={() => setActiveTab('readme')}
              >
                <BookOpen size={16} />
                <span>From the README</span>
                <span className="tab-counter">{suggestions.length}</span>
              </button>
            </div>

            {/* Tab 1: Issues View */}
            {activeTab === 'issues' && (
              <>
                {/* Filter and stats control strip */}
                <div className="controls-strip">
                  <label className="filter-toggle-label">
                    <input
                      type="checkbox"
                      checked={showAllIssues}
                      onChange={(e) => setShowAllIssues(e.target.checked)}
                    />
                    <span>
                      Show claimed &amp; stale issues{' '}
                      {hiddenCount > 0 && !showAllIssues && (
                        <span style={{ color: 'var(--text-subtle)' }}>({hiddenCount} hidden)</span>
                      )}
                    </span>
                  </label>

                  <div className="status-counts-summary">
                    <span style={{ color: '#9bd3ac' }}>
                      ● {issues.filter((i) => i.status === 'safe').length} Safe
                    </span>
                    <span style={{ color: 'var(--muted)' }}>
                      ● {issues.filter((i) => i.status === 'unclear').length} Unclear
                    </span>
                    <span style={{ color: '#ef4444' }}>
                      ● {issues.filter((i) => i.status === 'claimed').length} Claimed
                    </span>
                    <span style={{ color: '#f59e0b' }}>
                      ● {issues.filter((i) => i.status === 'stale').length} Stale
                    </span>
                  </div>
                </div>

                {/* Issues List or Empty State */}
                {visibleIssues.length === 0 ? (
                  <div className="search-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
                    <Filter size={36} color="var(--text-subtle)" style={{ margin: '0 auto 1rem' }} />
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>No issues match current filter</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                      {showAllIssues
                        ? 'No issues were found for the selected labels.'
                        : 'All matched issues are currently claimed or stale. Toggle "Show claimed & stale" or check the README tab.'}
                    </p>
                    {!showAllIssues && hiddenCount > 0 && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setShowAllIssues(true)}
                      >
                        Show All {issues.length} Issues
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="issues-stack">
                    {visibleIssues.map((scored) => (
                      <IssueCard
                        key={scored.issue.id || scored.issue.number}
                        scoredIssue={scored}
                        repo={currentRepo}
                      />
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Tab 2: README Suggestions View */}
            {activeTab === 'readme' && (
              <ReadmeSuggestions suggestions={suggestions} repo={currentRepo} />
            )}
          </div>
        )}

        {/* Track Screen */}
        {currentView === 'track' && (
          <TrackView prefilledRepo={currentRepo} onToast={addToast} />
        )}
      </main>

      {/* Floating Toast Notification */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast">
            <Sparkles size={14} color="var(--ember)" />
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {/* App Footer */}
      <footer className="footer">
        <p>
          myOpenSource · Built for <strong>Devf8rge x Hacktoberfest 2026</strong>
        </p>
      </footer>
    </div>
  );
}
