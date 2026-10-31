/**
 * Centralized API Module for myOpenSource
 *
 * Implements the contract defined in AGENTS.md.
 * Automatically toggles between Mock data and Real FastAPI backend
 * based on VITE_USE_MOCK environment variable (default: 1).
 */

import {
  MOCK_SCORED_ISSUES,
  MOCK_README_SUGGESTIONS,
  MOCK_INITIAL_WATCHES
} from './mock/mockData.js';

// Configuration
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
// Check if mock mode is explicitly requested (default: false / live backend mode)
const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1' || import.meta.env.VITE_USE_MOCK === 'true';

// Helper for mock latency to test UI skeletons/loaders
const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

// LocalStorage key for mock watches persistence across page reloads
const MOCK_WATCHES_KEY = 'myopensource_mock_watches';

function getMockWatches() {
  try {
    const raw = localStorage.getItem(MOCK_WATCHES_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn('Failed to read mock watches from localStorage', err);
  }
  return [];
}

function saveMockWatches(watches) {
  try {
    localStorage.setItem(MOCK_WATCHES_KEY, JSON.stringify(watches));
  } catch (err) {
    console.warn('Failed to save mock watches to localStorage', err);
  }
}

/**
 * Custom Error class capturing API error codes
 */
export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code || 'UNKNOWN_ERROR';
    this.status = status || 500;
  }
}

/**
 * Standard fetch wrapper for real backend communication
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, { ...options, headers });
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errCode = data?.error?.code || `HTTP_${response.status}`;
      const errMessage = data?.error?.message || response.statusText || 'An error occurred';
      throw new ApiError(errMessage, errCode, response.status);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Handle network offline / fetch failed
    throw new ApiError(
      'Unable to connect to the server. Please check your network or try again.',
      'NETWORK_ERROR',
      0
    );
  }
}

/**
 * Helper to split repo string "owner/name"
 */
function parseRepoSlug(repoOrUrl) {
  const cleaned = repoOrUrl.trim().replace(/^https?:\/\/github\.com\//i, '').replace(/\/+$/, '');
  const parts = cleaned.split('/');
  if (parts.length < 2 || !parts[0] || !parts[1]) {
    throw new ApiError('Invalid repository URL or format. Expected "owner/repo"', 'INVALID_REPO', 400);
  }
  return `${parts[0]}/${parts[1]}`;
}

// ==========================================
// EXPORTED API FUNCTIONS (THE CONTRACT)
// ==========================================

/**
 * 1. Analyze Repo (POST /api/repos)
 * @param {string} url - GitHub repo URL or "owner/repo" slug
 * @param {string[]} [tags] - Labels to match, default ["good first issue"]
 * @returns {Promise<{ repo: string, issues: Array, note: string | null }>}
 */
export async function analyzeRepo(url, tags = ['good first issue']) {
  if (USE_MOCK) {
    await delay(500);

    const trimmed = (url || '').trim();
    if (!trimmed) {
      throw new ApiError('Please enter a repository URL or slug.', 'INVALID_REPO', 400);
    }

    // Special testing fixtures for error states in mock mode
    if (trimmed.includes('invalid') || trimmed === 'foo') {
      throw new ApiError('Repository path format is invalid. Example: "pallets/flask"', 'INVALID_REPO', 400);
    }
    if (trimmed.includes('notfound') || trimmed.includes('404')) {
      throw new ApiError('Repository not found on GitHub or is private.', 'REPO_NOT_FOUND', 404);
    }
    if (trimmed.includes('ratelimit') || trimmed.includes('429')) {
      throw new ApiError('GitHub API rate limit exceeded. Please wait a moment before trying again.', 'RATE_LIMITED', 429);
    }

    let repoSlug = 'pallets/flask';
    try {
      repoSlug = parseRepoSlug(trimmed);
    } catch {
      repoSlug = trimmed;
    }

    // Filter mock issues based on tags if tags are specified
    // In mock, return issues matching tags or all sample issues
    let issues = [...MOCK_SCORED_ISSUES];
    let note = null;

    if (tags && tags.length > 0 && !tags.some(t => t.toLowerCase().includes('good first') || t.toLowerCase().includes('good-first'))) {
      // simulate no match for obscure tags
      if (tags.includes('nonexistent-label')) {
        issues = [];
        note = 'No open issues matched these labels. Check the README suggestions below for contribution ideas!';
      }
    }

    return {
      repo: repoSlug,
      issues,
      note
    };
  }

  return apiRequest('/api/repos', {
    method: 'POST',
    body: JSON.stringify({ url, tags })
  });
}

/**
 * 2. Get Issues (GET /api/repos/{owner}/{name}/issues)
 * @param {string} repo - "owner/repo"
 * @param {string[]} [tags] - Array of tags
 * @param {string} [status] - Optional status filter: "safe" | "claimed" | "stale" | "unclear"
 * @returns {Promise<Array>} List of ScoredIssue
 */
export async function getIssues(repo, tags = [], status = null) {
  const slug = parseRepoSlug(repo);
  const [owner, name] = slug.split('/');

  if (USE_MOCK) {
    await delay(350);
    let results = [...MOCK_SCORED_ISSUES];
    if (status) {
      results = results.filter((s) => s.status === status);
    }
    return results;
  }

  const queryParams = new URLSearchParams();
  if (tags && tags.length > 0) {
    queryParams.append('tags', tags.join(','));
  }
  if (status) {
    queryParams.append('status', status);
  }

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/api/repos/${owner}/${name}/issues${queryStr}`);
}

/**
 * 3. Get Suggestions from README (GET /api/repos/{owner}/{name}/suggestions)
 * @param {string} repo - "owner/repo"
 * @returns {Promise<Array>} List of ReadmeSuggestion
 */
export async function getSuggestions(repo) {
  const slug = parseRepoSlug(repo);
  const [owner, name] = slug.split('/');

  if (USE_MOCK) {
    await delay(400);
    return [...MOCK_README_SUGGESTIONS];
  }

  return apiRequest(`/api/repos/${owner}/${name}/suggestions`);
}

/**
 * 4. Explain Issue with AI (GET /api/issues/{owner}/{name}/{number}/explain)
 * @param {string} repo - "owner/repo"
 * @param {number} number - Issue number
 * @returns {Promise<Object>} AIInsight
 */
export async function explainIssue(repo, number) {
  const slug = parseRepoSlug(repo);
  const [owner, name] = slug.split('/');

  if (USE_MOCK) {
    await delay(600);
    // Find matching mock issue or synthesize a realistic one
    const match = MOCK_SCORED_ISSUES.find((item) => item.issue.number === Number(number));
    if (match && match.ai) {
      return match.ai;
    }
    return {
      summary: `Issue #${number} requires targeted adjustments in the repository. Maintainers have marked it for prospective contributors.`,
      files_to_touch: ['src/main.py', 'tests/test_main.py'],
      skills_needed: ['Git', 'Python/JS', 'Testing'],
      first_steps: [
        'Read the issue description and review reproduction details',
        'Locate the relevant code modules locally',
        'Add tests to verify your fix and confirm existing tests pass'
      ],
      beginner_rating: 8,
      provider: 'fallback'
    };
  }

  return apiRequest(`/api/issues/${owner}/${name}/${number}/explain`);
}

/**
 * 5. Create Watch (POST /api/watch)
 * @param {Object} watchIn - { repo, tags, channel, contact }
 * @returns {Promise<Object>} Watch
 */
export async function createWatch(watchIn) {
  const { repo, tags = ['good first issue'], channel = 'telegram', contact } = watchIn;

  if (!repo || !contact) {
    throw new ApiError('Repository and contact (chat ID) are required.', 'INVALID_INPUT', 400);
  }

  const slug = parseRepoSlug(repo);

  if (USE_MOCK) {
    await delay(450);
    const watches = getMockWatches();
    const newWatch = {
      id: Date.now(),
      repo: slug,
      tags: Array.isArray(tags) ? tags : [tags],
      channel,
      contact: String(contact).trim(),
      created_at: new Date().toISOString()
    };
    watches.unshift(newWatch);
    saveMockWatches(watches);
    return newWatch;
  }

  return apiRequest('/api/watch', {
    method: 'POST',
    body: JSON.stringify({
      repo: slug,
      tags: Array.isArray(tags) ? tags : [tags],
      channel,
      contact: String(contact).trim()
    })
  });
}

/**
 * 6. List Watches (GET /api/watch?contact=)
 * @param {string} [contact] - Telegram chat ID or email
 * @returns {Promise<Array>} List of Watch
 */
export async function listWatches(contact = '') {
  const trimmed = (contact ? String(contact) : '').trim();
  // Privacy & Contract Rule: Never query or expose global watches or other users' watches
  if (!trimmed) {
    return [];
  }

  if (USE_MOCK) {
    await delay(300);
    const watches = getMockWatches();
    return watches.filter((w) => w.contact === trimmed);
  }

  const queryStr = `?contact=${encodeURIComponent(trimmed)}`;
  return apiRequest(`/api/watch${queryStr}`);
}

/**
 * 7. Delete Watch (DELETE /api/watch/{id})
 * @param {number|string} id - Watch ID
 * @returns {Promise<{ ok: boolean }>}
 */
export async function deleteWatch(id) {
  if (USE_MOCK) {
    await delay(300);
    const watches = getMockWatches();
    const updated = watches.filter((w) => String(w.id) !== String(id));
    saveMockWatches(updated);
    return { ok: true };
  }

  return apiRequest(`/api/watch/${id}`, {
    method: 'DELETE'
  });
}

/**
 * 8. Trigger Watch Poller Check (POST /api/watch/check-now)
 * For demo purposes: forces immediate check and notification trigger
 * @returns {Promise<{ checked: number, notified: number }>}
 */
export async function checkNow() {
  if (USE_MOCK) {
    await delay(700);
    return {
      checked: 2,
      notified: 1
    };
  }

  return apiRequest('/api/watch/check-now', {
    method: 'POST'
  });
}

/**
 * 9. Test Notification Channel (POST /api/watch/test-notify)
 * @param {string} contact - Telegram Chat ID
 * @param {string} [channel='telegram']
 * @returns {Promise<{ ok: boolean, message: string }>}
 */
export async function testNotify(contact, channel = 'telegram') {
  if (USE_MOCK) {
    await delay(500);
    return { ok: true, message: 'Mock notification dispatched to chat ID.' };
  }

  return apiRequest('/api/watch/test-notify', {
    method: 'POST',
    body: JSON.stringify({ contact: String(contact).trim(), channel })
  });
}

/**
 * 10. Get Watcher & Bot Status (GET /api/watch/status)
 * @returns {Promise<Object>}
 */
export async function getWatchStatus() {
  if (USE_MOCK) {
    await delay(300);
    const mockList = getMockWatches();
    return {
      status: 'ok',
      scheduler: { enabled: true, running: true, poll_interval_seconds: 10 },
      bot: { enabled: true, running: true, token_configured: true },
      watched_repos_count: mockList.length,
      watched_repos: [...new Set(mockList.map((w) => w.repo))]
    };
  }

  return apiRequest('/api/watch/status');
}

