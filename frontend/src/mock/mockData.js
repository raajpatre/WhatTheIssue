import sampleIssuesRaw from './sample_issues.json';

export const MOCK_SCORED_ISSUES = [
  {
    issue: sampleIssuesRaw[0],
    score: 95,
    status: 'safe',
    reasons: [
      'Clear description with steps to reproduce and expected output',
      'No assignees and no linked open pull requests',
      'Maintainer explicitly commented "PRs welcome"'
    ],
    ai: {
      summary: 'docs/install.md has a one-character typo ("pip instal" instead of "pip install"). Fixing this ensures new users can install the package smoothly.',
      files_to_touch: ['docs/install.md'],
      skills_needed: ['Markdown', 'Git basics'],
      first_steps: [
        'Fork and clone the repository',
        'Open docs/install.md and find the Quick start command',
        'Change "pip instal requests" to "pip install requests"',
        'Commit with a clean message and open a Pull Request'
      ],
      beginner_rating: 10,
      provider: 'gemini'
    }
  },
  {
    issue: sampleIssuesRaw[1],
    score: 30,
    status: 'claimed',
    reasons: [
      'Already assigned to @eager-contributor',
      'An open pull request is already linked to this issue',
      'Active comments indicate work is currently underway'
    ],
    ai: {
      summary: 'Unit tests are requested for date parser utilities in src/utils/dates.py. Note that a PR is already active, so check before duplicating work.',
      files_to_touch: ['tests/test_dates.py', 'src/utils/dates.py'],
      skills_needed: ['Python', 'pytest', 'datetime'],
      first_steps: [
        'Review the open PR to see if all edge cases are addressed',
        'Ask in comments if extra test cases are welcome'
      ],
      beginner_rating: 6,
      provider: 'gemini'
    }
  },
  {
    issue: sampleIssuesRaw[2],
    score: 45,
    status: 'stale',
    reasons: [
      'No comments or updates for over 18 months',
      'Underlying codebase has evolved since this was created',
      'Needs confirmation that load_config still crashes on missing config.yaml'
    ],
    ai: {
      summary: 'When config.yaml is absent, load_config triggers an unhandled exception stack trace. It should catch FileNotFoundError and print a friendly message.',
      files_to_touch: ['src/config.py'],
      skills_needed: ['Python', 'Exception handling', 'YAML'],
      first_steps: [
        'Check current implementation of load_config in src/config.py',
        'Run existing tests to ensure baseline passes',
        'Wrap file loading with friendly error reporting'
      ],
      beginner_rating: 7,
      provider: 'gemini'
    }
  },
  {
    issue: sampleIssuesRaw[3],
    score: 20,
    status: 'unclear',
    reasons: [
      'Extremely brief description ("fix it / broken")',
      'No reproduction steps, environment details, or logs provided',
      'Risk of wasted effort without maintainer clarification'
    ],
    ai: {
      summary: 'The issue contains only "fix it" and "broken" without any context or steps. Asking the maintainer for clarification is recommended before writing code.',
      files_to_touch: [],
      skills_needed: ['Issue triage'],
      first_steps: [
        'Comment politely asking for reproduction steps and log outputs',
        'Check if other issues mention the same failure'
      ],
      beginner_rating: 2,
      provider: 'gemini'
    }
  }
];

export const MOCK_README_SUGGESTIONS = [
  {
    title: 'Add Docker quickstart instructions',
    description: 'The README mentions containerization support, but lacks a concise docker run or docker-compose snippet in the Setup section.',
    area: 'setup',
    why_beginner_friendly: 'Great way to verify local Docker setup without needing to touch complex application code.'
  },
  {
    title: 'Update broken documentation badge',
    description: 'The coverage status badge in README.md points to an outdated GitHub Actions workflow file that was renamed.',
    area: 'docs',
    why_beginner_friendly: 'Single-line markdown fix with immediate visual feedback in the README.'
  },
  {
    title: 'Add docstrings and type annotations to date utilities',
    description: 'src/utils/dates.py contains helper methods that currently lack parameter and return type hints.',
    area: 'bugfix',
    why_beginner_friendly: 'Self-contained helper functions with straightforward inputs and outputs.'
  },
  {
    title: 'Add example env file and configuration documentation',
    description: 'Provide an annotated .env.example explaining each setting with sensible defaults for local testing.',
    area: 'docs',
    why_beginner_friendly: 'Helpful for all future contributors; straightforward markdown and template creation.'
  }
];

export const MOCK_INITIAL_WATCHES = [
  {
    id: 1,
    repo: 'demo-org/demo-repo',
    tags: ['good first issue', 'documentation'],
    channel: 'telegram',
    contact: '123456789',
    created_at: new Date(Date.now() - 3600000 * 24).toISOString()
  }
];
