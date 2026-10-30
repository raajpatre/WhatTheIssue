import React, { useState, useEffect } from 'react';
import { Bell, Send, Trash2, RefreshCw, CheckCircle2, MessageSquare, AlertCircle } from 'lucide-react';
import { createWatch, listWatches, deleteWatch, checkNow } from '../api';

const LOCAL_STORAGE_CONTACT_KEY = 'myopensource_telegram_contact';

export default function TrackView({ prefilledRepo = '', onToast }) {
  const [repo, setRepo] = useState(prefilledRepo);
  const [tagsInput, setTagsInput] = useState('good first issue');
  const [contact, setContact] = useState('');
  const [watches, setWatches] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [checkingNow, setCheckingNow] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Load remembered contact from localStorage on mount
  useEffect(() => {
    try {
      const savedContact = localStorage.getItem(LOCAL_STORAGE_CONTACT_KEY);
      if (savedContact) {
        setContact(savedContact);
        loadWatches(savedContact);
      } else {
        loadWatches('');
      }
    } catch (err) {
      console.warn('Could not read from localStorage', err);
      loadWatches('');
    }
  }, []);

  // Sync prefilled repo when prop changes
  useEffect(() => {
    if (prefilledRepo) {
      setRepo(prefilledRepo);
    }
  }, [prefilledRepo]);

  const loadWatches = async (contactVal) => {
    setLoadingList(true);
    try {
      const data = await listWatches(contactVal);
      setWatches(data || []);
    } catch (err) {
      console.error('Failed to load watches', err);
    } finally {
      setLoadingList(false);
    }
  };

  const handleCreateWatch = async (e) => {
    e.preventDefault();
    if (!repo.trim() || !contact.trim()) {
      setFeedback({ type: 'error', message: 'Repository and Telegram Chat ID are required.' });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      // Parse tags
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const created = await createWatch({
        repo: repo.trim(),
        tags: tags.length > 0 ? tags : ['good first issue'],
        channel: 'telegram',
        contact: contact.trim()
      });

      // Save contact in localStorage
      try {
        localStorage.setItem(LOCAL_STORAGE_CONTACT_KEY, contact.trim());
      } catch (err) {
        console.warn('Failed to save contact to localStorage', err);
      }

      setFeedback({
        type: 'success',
        message: `Now tracking ${created.repo}! You'll receive a Telegram alert when a matching issue appears.`
      });

      if (onToast) {
        onToast(`Tracking ${created.repo}`);
      }

      // Refresh watches list
      loadWatches(contact.trim());
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to create watch.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteWatch = async (id, repoName) => {
    try {
      await deleteWatch(id);
      setWatches(watches.filter((w) => w.id !== id));
      if (onToast) {
        onToast(`Removed watch for ${repoName}`);
      }
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to remove watch.' });
    }
  };

  const handleCheckNow = async () => {
    setCheckingNow(true);
    try {
      const res = await checkNow();
      const msg = `Checked ${res.checked} repo(s). Dispatched ${res.notified} alert(s)!`;
      setFeedback({ type: 'success', message: msg });
      if (onToast) onToast(msg);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Check failed.' });
    } finally {
      setCheckingNow(false);
    }
  };

  return (
    <div className="track-view">
      {/* Left: Create Watch Form */}
      <div className="track-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.5rem' }}>
          <Bell size={22} color="#3b82f6" />
          <h3>Track a Repository</h3>
        </div>
        <p className="track-card-desc">
          Receive real-time alerts on Telegram the moment an issue matching your criteria is published.
        </p>

        {feedback && (
          <div className={`alert-banner ${feedback.type}`}>
            {feedback.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            <span>{feedback.message}</span>
          </div>
        )}

        <form onSubmit={handleCreateWatch}>
          <div className="form-group">
            <label className="form-label">Repository (owner/name)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. demo-org/demo-repo"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Issue Labels (comma separated)</label>
            <input
              type="text"
              className="form-input"
              placeholder="good first issue, help wanted"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
            />
            <div className="form-helper">Default: good first issue</div>
          </div>

          <div className="form-group">
            <label className="form-label">Telegram Chat ID</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. 123456789"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              required
            />
          </div>

          <div className="bot-helper-box">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>
              <MessageSquare size={14} color="#60a5fa" />
              <span>How to find your Telegram Chat ID</span>
            </div>
            <span>Open our Telegram bot, send <code>/start</code>, and paste the numeric ID here.</span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
              style={{ flex: 1 }}
            >
              <Send size={15} />
              <span>{submitting ? 'Setting Watch...' : 'Start Watching'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Right: Active Watches & Demo Check Trigger */}
      <div className="track-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <h3>Your Watched Repos</h3>
          <button
            className="btn btn-secondary"
            onClick={handleCheckNow}
            disabled={checkingNow}
            title="Polls tracked repos immediately (Live Demo Feature)"
            style={{ fontSize: '0.8125rem', padding: '0.4rem 0.75rem' }}
          >
            <RefreshCw size={13} className={checkingNow ? 'animate-spin' : ''} />
            <span>{checkingNow ? 'Checking...' : 'Check Now (Demo)'}</span>
          </button>
        </div>

        <p className="track-card-desc">
          Repos currently monitored for new beginner issues. Use <strong>Check Now</strong> to trigger an instant check during demo presentations.
        </p>

        {loadingList ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="skeleton skeleton-title" style={{ width: '100%', height: '54px' }} />
            <div className="skeleton skeleton-title" style={{ width: '100%', height: '54px' }} />
          </div>
        ) : watches.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ color: 'var(--text-subtle)', fontSize: '0.875rem' }}>
              No repositories watched yet. Add one on the left!
            </p>
          </div>
        ) : (
          <div className="watches-list">
            {watches.map((w) => (
              <div key={w.id} className="watch-item">
                <div className="watch-item-info">
                  <span className="watch-item-repo">{w.repo}</span>
                  <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                    {w.tags?.map((t, idx) => (
                      <span key={idx} className="gh-label" style={{ fontSize: '0.6875rem' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                  <span className="watch-item-contact">
                    Chat ID: {w.contact}
                  </span>
                </div>

                <button
                  type="button"
                  className="btn btn-outline-danger"
                  onClick={() => handleDeleteWatch(w.id, w.repo)}
                  title="Delete watch"
                  style={{ padding: '0.4rem 0.6rem' }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
