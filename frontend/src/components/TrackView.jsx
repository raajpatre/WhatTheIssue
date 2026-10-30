import React, { useState, useEffect } from 'react';
import { Bell, Send, Trash2, RefreshCw, CheckCircle2, MessageSquare, AlertCircle, ShieldAlert } from 'lucide-react';
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
      if (savedContact && savedContact.trim()) {
        const trimmed = savedContact.trim();
        setContact(trimmed);
        loadWatches(trimmed);
      } else {
        setWatches([]);
      }
    } catch {
      // LocalStorage access restricted or unavailable
      setWatches([]);
    }
  }, []);

  // Sync prefilled repo when prop changes
  useEffect(() => {
    if (prefilledRepo) {
      setRepo(prefilledRepo);
    }
  }, [prefilledRepo]);

  const loadWatches = async (contactVal) => {
    const trimmed = (contactVal || '').trim();
    if (!trimmed) {
      setWatches([]);
      return;
    }

    setLoadingList(true);
    try {
      const data = await listWatches(trimmed);
      setWatches(data || []);
    } catch (err) {
      // Security: Do not expose chat ID in error message or logs
      console.error('Failed to load tracked repositories');
      setFeedback({ type: 'error', message: 'Unable to retrieve tracked repositories. Please try again.' });
    } finally {
      setLoadingList(false);
    }
  };

  const handleContactBlur = () => {
    if (contact.trim()) {
      loadWatches(contact.trim());
    } else {
      setWatches([]);
    }
  };

  const handleCreateWatch = async (e) => {
    e.preventDefault();
    const cleanRepo = repo.trim();
    const cleanContact = contact.trim();

    if (!cleanRepo || !cleanContact) {
      setFeedback({ type: 'error', message: 'Repository and Telegram Chat ID are required.' });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const created = await createWatch({
        repo: cleanRepo,
        tags: tags.length > 0 ? tags : ['good first issue'],
        channel: 'telegram',
        contact: cleanContact
      });

      // Remember contact locally
      try {
        localStorage.setItem(LOCAL_STORAGE_CONTACT_KEY, cleanContact);
      } catch {
        // LocalStorage fallback
      }

      setFeedback({
        type: 'success',
        message: `Now tracking ${created.repo}! You will receive a Telegram alert when a matching issue appears.`
      });

      if (onToast) {
        onToast(`Tracking ${created.repo}`);
      }

      // Refresh list for this user's chat ID
      loadWatches(cleanContact);
    } catch (err) {
      // Security: Never print contact/chat ID in error messages
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
      setFeedback({ type: 'error', message: 'Failed to remove watch. Please try again.' });
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
      setFeedback({ type: 'error', message: 'Check failed. Please verify server connection.' });
    } finally {
      setCheckingNow(false);
    }
  };

  // Helper to safely format chat ID without exposing full raw numbers
  const maskChatId = (idStr) => {
    if (!idStr) return '';
    const str = String(idStr);
    if (str.length <= 4) return '••••';
    return `••••${str.slice(-4)}`;
  };

  return (
    <div className="track-view">
      {/* Left Column: Create Watch Form */}
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
              onBlur={handleContactBlur}
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

          {/* Privacy Notice Required by PART-D specification */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem', marginTop: '1rem', color: 'var(--text-subtle)', fontSize: '0.75rem', lineHeight: 1.4 }}>
            <ShieldAlert size={14} style={{ flexShrink: 0, marginTop: '2px', color: '#94a3b8' }} />
            <span>Demo app: no login. Anyone who knows your chat ID could see your tracked repos.</span>
          </div>
        </form>
      </div>

      {/* Right Column: Watched Repos */}
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
        ) : !contact.trim() ? (
          /* Empty localStorage / new device state specified in PART-D */
          <div style={{ textAlign: 'center', padding: '3rem 1.25rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
            <MessageSquare size={32} color="var(--text-subtle)" style={{ margin: '0 auto 0.75rem' }} />
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.375rem' }}>
              Enter your Telegram chat ID to see your tracked repos
            </h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', maxWidth: '300px', margin: '0 auto' }}>
              We look up watches keyed strictly by your chat ID. There is no public list.
            </p>
          </div>
        ) : watches.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ color: 'var(--text-subtle)', fontSize: '0.875rem' }}>
              No repositories watched yet for this chat ID. Add one on the left!
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
                    Chat ID: {maskChatId(w.contact)}
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
