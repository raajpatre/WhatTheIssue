import React, { useState } from 'react';
import { Search, ShieldCheck, BellRing, BookOpen, Plus, X } from 'lucide-react';

const POPULAR_TAGS = ['good first issue', 'help wanted', 'beginner'];
const EXAMPLE_REPOS = [
  'demo-org/demo-repo',
  'pallets/flask',
  'fastapi/fastapi'
];

export default function HomeHero({ onAnalyze, loading }) {
  const [url, setUrl] = useState('');
  const [selectedTags, setSelectedTags] = useState(['good first issue']);
  const [customTag, setCustomTag] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const toggleTag = (tag) => {
    if (selectedTags.includes(tag)) {
      if (selectedTags.length > 1) {
        setSelectedTags(selectedTags.filter((t) => t !== tag));
      }
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const handleAddCustomTag = (e) => {
    if (e.key === 'Enter' || e.type === 'blur') {
      const trimmed = customTag.trim().toLowerCase();
      if (trimmed && !selectedTags.includes(trimmed)) {
        setSelectedTags([...selectedTags, trimmed]);
      }
      setCustomTag('');
      setShowCustomInput(false);
    }
  };

  const removeTag = (tagToRemove, e) => {
    e.stopPropagation();
    if (selectedTags.length > 1) {
      setSelectedTags(selectedTags.filter((t) => t !== tagToRemove));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onAnalyze(url.trim(), selectedTags);
    }
  };

  const handleExampleClick = (example) => {
    setUrl(example);
    onAnalyze(example, selectedTags);
  };

  return (
    <div className="hero-section">
      <h1 className="hero-title">
        <span className="hero-title-gradient">Labels lie. Find issues that are </span>
        <span className="hero-title-highlight">actually safe to start.</span>
      </h1>

      <p className="hero-subtitle">
        Most &quot;good first issues&quot; are already claimed, abandoned, or require 10 hours of context.
        We scan PRs, comments, and activity to give you verified starter tasks.
      </p>

      {/* Search Input Box */}
      <div className="search-card">
        <form onSubmit={handleSubmit}>
          <div className="search-input-group">
            <div className="input-wrapper">
              <Search className="input-icon" size={19} />
              <input
                type="text"
                className="search-input"
                placeholder="Paste GitHub repository URL or owner/name (e.g. demo-org/demo-repo)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                autoFocus
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary search-btn"
              disabled={loading || !url.trim()}
            >
              {loading ? 'Analyzing...' : 'Analyze Repo'}
            </button>
          </div>

          {/* Tag Chips */}
          <div className="tag-selection">
            <span className="tag-label">Tags:</span>
            {POPULAR_TAGS.map((tag) => {
              const active = selectedTags.includes(tag);
              return (
                <button
                  type="button"
                  key={tag}
                  className={`chip ${active ? 'active' : ''}`}
                  onClick={() => toggleTag(tag)}
                >
                  {tag}
                </button>
              );
            })}

            {/* Custom tags added by user */}
            {selectedTags
              .filter((t) => !POPULAR_TAGS.includes(t))
              .map((tag) => (
                <span key={tag} className="chip active">
                  {tag}
                  <X
                    size={13}
                    style={{ marginLeft: '4px', cursor: 'pointer' }}
                    onClick={(e) => removeTag(tag, e)}
                  />
                </span>
              ))}

            {showCustomInput ? (
              <input
                type="text"
                className="custom-tag-input"
                placeholder="Press Enter..."
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
                onKeyDown={handleAddCustomTag}
                onBlur={handleAddCustomTag}
                autoFocus
              />
            ) : (
              <button
                type="button"
                className="chip"
                onClick={() => setShowCustomInput(true)}
              >
                <Plus size={13} />
                <span>Custom tag</span>
              </button>
            )}
          </div>
        </form>

        {/* Quick Example Repos */}
        <div className="example-repos">
          <span>Try an example:</span>
          {EXAMPLE_REPOS.map((ex) => (
            <button
              key={ex}
              type="button"
              className="example-repo-link"
              onClick={() => handleExampleClick(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* How it works strip */}
      <div className="how-it-works-grid">
        <div className="step-card">
          <div className="step-number">Step 01</div>
          <div className="step-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Search size={18} color="#3b82f6" />
            <span>Paste Any Repo</span>
          </div>
          <p className="step-desc">
            Provide a GitHub URL. We fetch all open beginner issues and README instructions via read-only APIs.
          </p>
        </div>

        <div className="step-card">
          <div className="step-number">Step 02</div>
          <div className="step-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={18} color="#10b981" />
            <span>Heuristic Scoring</span>
          </div>
          <p className="step-desc">
            We flag open PR collisions, assignee inactivity, and stale threads to sort safe issues from claimed traps.
          </p>
        </div>

        <div className="step-card">
          <div className="step-number">Step 03</div>
          <div className="step-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BellRing size={18} color="#8b5cf6" />
            <span>AI Guide & Watcher</span>
          </div>
          <p className="step-desc">
            AI explains what files to touch in plain English. Track the repo to get alerted on Telegram the moment a fresh issue drops.
          </p>
        </div>
      </div>
    </div>
  );
}
