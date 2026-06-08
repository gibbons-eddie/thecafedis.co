- Background scroller uses 24 copies per row with 4.166% translation for seamless effect
- Background text styling: oklch(22% 0.04 208.734), 2rem size, 0.3 opacity, 0.5rem row padding
- Logo animation: animate-spin-slow class completes one rotation every 60 seconds
- Main content background uses 95% opacity: oklch(19.533% 0.03365 208.734 / 0.95)
- CSS @keyframes MUST be at top level, never nested inside :root or other selectors - browsers ignore them otherwise
- For seamless scrolling: use width: max-content on animation container and display: inline-block on child elements
- All scroll animations run at 35 seconds duration (10 seconds slower than original 25s)
- Source CSS: styles/styles.css (outside static/ to avoid WhiteNoise post-processing), Compiled CSS: static/dist/styles.css
- Dependencies: Django 5.2.3, WhiteNoise for static files, Tailwind CSS v4.1.10
- Background scroller lives in templates/base.html (lines 12-123) so it appears on all pages
- Refresh static files: python3 manage.py collectstatic --noinput --clear
- Run dev server: python3 manage.py runserver (runs on http://localhost:8000)
- Animation translation math: 100% ÷ number of copies = translation percentage (e.g., 100/24 = 4.166%)
- Always compile Tailwind: npx tailwindcss -i styles/styles.css -o static/dist/styles.css
- Background text color: oklch(22% 0.04 208.734) with 0.3 opacity
- Do not use emojis in responses or planning documents or anything else ever.
- Do not use `!important` in CSS code, it's bad coding practice.
- Always store planning documents in `thecafedis.co planning` directory on the Desktop
- When I say to start or stop the dev server, always use the start and stop scripts inside the `thecafedisite` directory
- Try to minimize comments. If the method is relatively straightforward and easy to understand without comments, remove the comments and/or JAVADOCs
- Use Chrome MCP instead of the playwright plugin as much as possible
- Any PLaywright screengrabs must be saved to `.playwright-mcp` folder

## Planning File Convention
- All Claude planning files stored in: /Users/eddiegibbons/.claude/plans/
- Filename format: YYYY-MM-DD-brief-topic-description.md (e.g., 2025-11-27-menu-btn-hover-impl.md)
- File header must include: Model name (Claude Sonnet 4.5), full date, and status
- Header template: # [Plan Title] | **Model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | **Date:** [Month DD, YYYY] | **Status:** [Planning/Implementation/Complete]
- Keep old plan files as backup when creating consolidated versions
- Reference examples: 2025-11-27-menu-btn-hover-impl.md (implementation), 2025-11-28-unpoly-persistent-bg-features.md (planning)

## Site Testing Agent

A comprehensive browser-based testing agent is available for validating the dev server.

### To Run Tests
Say: "Test the dev server at localhost:8000 and save results to the planning folder"

### Test Documentation
- Test specification: `/Users/eddiegibbons/Desktop/thecafedis.co planning/site-testing-agent.md`
- Results template: `/Users/eddiegibbons/Desktop/thecafedis.co planning/test-results-template.md`

### Test Categories
1. Public Pages (Homepage, Music, Videos, Stream)
2. Authentication (Login, Protected Routes)
3. Dashboard Admin (Music, Videos, Career, Skills, Profiles, Comments)
4. API Endpoints (Play counts, View counts, Comment submission)
5. Edge Cases (Empty states, 404s, Form validation, Navigation)
6. Visual/UI (Styling, Animations, Responsive design)

### Output
Test results saved to: `/Users/eddiegibbons/Desktop/thecafedis.co planning/test-results-YYYY-MM-DD.md`