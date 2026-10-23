# AthleteIQ UI Audit and Phase 1 Plan

**Status:** Phase 1 complete; awaiting approval before implementation.

## Scope and repository reality

The current frontend is a React 18 single-page application built with Vite.
It uses JavaScript/JSX, React Router, and a hand-written `styles.css`. It does
not currently use Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui,
Recharts, or Framer Motion. The authenticated experience is backed by an
existing FastAPI service; route behavior, data fetching, assessment logic,
API contracts, and authentication are out of scope for a visual redesign.

The design brief says “AthliteIQ,” while the repository and running app use
“AthleteIQ.” This audit retains the repository's current spelling pending
confirmation.

## Screen audit

| Route / screen | Primary job to be done | Current friction and hierarchy issues | Proposed visual / UX direction |
|---|---|---|---|
| `/` — Home | Explain the product and lead athletes to their first assessment. | Centered generic hero, gradient-highlighted headline, four equal stat cards, and three equal feature cards. Stats have no context when the database is empty. Supported tests form a long, undifferentiated grid. | Editorial left-aligned headline and one primary “Create your profile” action. Use a compact proof strip for real platform counts; use numbered journal-style sections and a denser exercise index with type/unit metadata. Keep empty/error data states explicit. |
| `/login` — Login | Return an existing user to their athlete/scout workspace. | Title, description, and a generic form card have similar visual weight; no visible field labels as eyebrows, no brand context, and the registration path competes with the submit action. | A quiet, narrow account page with one serif title, one ink primary action, labeled fields, and a subdued sign-up link. Preserve existing auth behavior. |
| `/signup` — Registration/profile | Create an account with role and athlete profile information. | Long form mixes role, identity, and optional athlete details in one equal-weight card. Athlete-only fields expand without a clear progressive hierarchy; primary action is below the full form. | Group required identity and optional profile details into labeled sections; retain current fields and submission contract. Make role choice clear and keep one primary “Create account” action. |
| `/dashboard` — Athlete history | Review past submissions, status, personal progress, and next action. | Four equally weighted stat cards precede a generic submissions card. “New test” and the empty-state CTA duplicate the primary action. Details expand as a second unstructured card; delete actions sit beside details with equal prominence. | Lead with the athlete's most useful score/trend, then a history section with source, status, date, score, and expandable details. Show one “Log session” action; place destructive delete behind a quieter control/confirmation. Use a journal-style empty state. |
| `/live` — Live assessment | Select an exercise, position safely, assess movement, and save an explainable result. | Functional live view is visually dense: camera, controls, exercise selector, instructions, stats, and result all compete. The camera panel and metric panel use equal card treatment; instructions repeat across the setup flow. | Treat the camera/pose frame as the primary instrument panel with corner ticks, a clear session index, one strong metric, and a compact cue. Keep setup guidance adjacent but secondary. Make model loading, permission denial, no-pose, active, completed, and error states intentional. Preserve the actual pose pipeline and source labels. |
| `/upload` — Video assessment | Select an exercise, upload a recorded clip, and review its result. | A generic drop zone and form card do not distinguish file selection from the primary action. Long analysis is communicated only by spinner text; its asynchronous status and timeout have little visual structure. | Frame upload as a small, deliberate workflow: exercise, file, validation, analysis status, result. Keep upload as the single primary action, with visible progress/timeout/error and concise result metrics. |
| `/leaderboard` — Public rankings | Compare personal-best results and filter the pool. | Five filters appear at once in a card; the age range is cramped, filters dominate results, and rank/score lack clear numeric alignment. Loading and empty states are generic. | Show the selected test and units prominently, default to a useful ranking, and put secondary filters behind a compact disclosure on mobile. Present rank and performance as aligned tabular data; label sample records. |
| `/scout` — Scout portal | Find athletes, inspect performance, and review flagged submissions. | Athlete search and flagged queue tabs use repeated generic tables. Loading/error states are inconsistent; errors from athlete/review requests can disappear. Wide tables can be difficult to scan on mobile. | Give athlete discovery and integrity review distinct section headers and indexes. Keep review actions explicit and visually secondary to assessment evidence. Use responsive athlete rows/cards and clear source/status labels. |
| Shared navigation / protected routes | Move between public, athlete, and scout areas without losing context. | Sticky full-width horizontal navigation is generic; all links are text-led. At mobile widths it wraps rather than becoming a designed navigation pattern. Protected-route loading is only a spinner. No dark-mode control or consistent page-header component exists. | Use the requested fixed desktop rail and a five-item mobile bottom bar only if the information architecture remains usable; highlight one active route with the signal marker. Standardize page headers, focus states, route loading, and theme toggle. |

## Cross-screen findings

- **Visual system:** `styles.css` currently defines a dark navy canvas, two blue
  card colors, green and cyan accents, a radial background, gradient cards and
  score bars, and a 14px card radius. The brief calls for light-first warm
  paper, ink, hairline rules, a single restrained signal red, and nearly
  square geometry.
- **Typography:** UI text uses a system/Inter stack; no display serif or
  dedicated mono data face is loaded. Numeric scores are not consistently
  treated as tabular editorial data.
- **Layout:** The shared content container is 1120px, with centered page
  content and repeated equal-column card grids. There is no 12-column
  composition, persistent left rail, or deliberate mobile bottom navigation.
- **Components:** Reusable styling is mostly global CSS classes (`.card`,
  `.btn`, `.grid-*`, `.badge`, `.alert`) plus inline styles. There are no
  shared PageHeader, SectionRule, StatBlock, DataTable, or EmptyState
  primitives.
- **Interaction/accessibility:** Native controls and labels are a useful base,
  but explicit `:focus-visible` treatment, disabled/loading consistency,
  reduced-motion rules, and designed keyboard/overlay behavior are not
  standardized. Some pages silently ignore fetch errors, which is a UX gap;
  changing request/business behavior would need to remain within the brief's
  guardrails.
- **Motion and signature:** No mask reveals, count-up treatment, rule lattice,
  mono module indexes, pull-stat, or corner registration marks exist.
- **Existing product strengths to preserve:** working API-driven exercise
  lists, authentication, user roles, server-side video analysis, actual
  MediaPipe Tasks live pose estimation, webcam permission diagnostics,
  skeleton overlay, exercise-specific feedback, result history, leaderboards,
  scout review, and explicit live/local/uploaded/sample source labels.

## Proposed design token sheet

The values below transcribe the design brief into an implementation-ready
token proposal. They are not applied to the application in Phase 1.

### Color

| Token | Paper theme | Night-session theme | Use |
|---|---|---|---|
| `--paper` | `#F6F2EA` | `#0E0D0B` | Page canvas |
| `--paper-2` | `#EDE8DD` | `#16150F` | Sunken/alternate surface and hover wash |
| `--card` | `#FFFDF8` | `#171612` | Module surface |
| `--ink` | `#14120F` | `#F4F0E6` | Primary text and primary button |
| `--ink-2` | `#4A453C` | `#B8B2A4` | Secondary text |
| `--ink-3` | `#8A8378` | `#776F62` | Metadata, units, labels |
| `--rule` | `#DCD5C7` | `#2A2822` | Hairline separators and table rules |
| `--signal` | `#E2452B` | `#FF5A3C` | Single active/focal accent |
| `--signal-soft` | `#FBE3DD` | Derived dark tint, pending contrast validation | Focus ring and quiet signal surface |
| `--good` | `#1E6B4F` | Same semantic green, validate contrast | Positive status/trend |
| `--warn` | `#A8641B` | Same semantic amber, validate contrast | Attention/review status |

**Accent constraint:** use signal red sparingly—prefer the active navigation
marker, one current-period/chart marker, or a single primary signal at a time.
Do not reintroduce gradients, glow, or filled decorative accents.

### Typography

| Role | Proposal | Application |
|---|---|---|
| Display serif | Instrument Serif | Large page titles and editorial pull-stat only |
| UI sans | Inter Tight | Body, controls, labels, and navigation |
| Numeric mono | Geist Mono | Scores, units, dates, indexes, and aligned table values |

Use at most these three families. The requested Next.js `next/font` loader is
not available in this Vite app; if staying on Vite, decide on a self-hosted
font asset or CSS font-face strategy before implementation. Do not fetch fonts
from a third-party runtime CDN.

| Scale token | Proposed style |
|---|---|
| `--type-display-xl` | `clamp(3.5rem, 8vw, 7rem)`, serif, `-0.03em`, `0.92` line-height |
| `--type-display-lg` | `clamp(2.5rem, 5vw, 4rem)`, serif, `-0.02em`, `0.95` line-height |
| `--type-h1` | `2rem`, serif or sans-semibold, `-0.02em` |
| `--type-h2` | `1.375rem`, sans-semibold, `-0.01em` |
| `--type-body` | `0.9375rem`, sans, `1.6` line-height, max width `68ch` |
| `--type-label` | `0.6875rem`, medium, uppercase, `0.14em` tracking |
| `--type-data-xl` | `3.5rem`, mono, `-0.02em`, tabular numerals |
| `--type-data` | `1.25rem`, mono, tabular numerals |

All numeric data should use `font-variant-numeric: tabular-nums`.

### Spacing, layout, shape, elevation, and motion

- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192px.
- **Page layout:** maximum width 1360px; horizontal gutters
  `clamp(20px, 5vw, 64px)`; 12-column grid with 24px gaps where screen space
  allows. Prefer asymmetric 5/7 or 7/5 layouts over uniform card grids.
- **Section rhythm:** full-width 1px `--rule` between major sections.
  Eyebrow + extending hairline + optional mono index (for example `03 / 07`).
- **Radius:** 2px controls; 4px cards; 999px status pills only.
- **Elevation:** none by default; optional `0 1px 0 var(--rule)` hairline.
  Reserve `0 24px 60px -30px rgba(20, 18, 15, .25)` for at most one floating
  element per screen.
- **Signature marks:** subtle rule lattice, mono module indexes, one data
  headline with unit/delta, editorial pull-stat with a signal rule, active
  signal stamp, and 6px registration ticks on only one to three hero panels.
- **Motion:** reveal content with a clipped upward translation over 480ms
  using `cubic-bezier(.16, 1, .3, 1)` and 40ms stagger; count important
  metrics once over 900ms without bounce; keep hover swaps at or below 120ms.
  Honor `prefers-reduced-motion` by disabling movement or using a brief fade.

## Proposed shared component API

The current app has CSS classes rather than a shadcn component layer. If
approved, define small shared React primitives that preserve existing route
and data behavior:

- `PageHeader`: title, optional description, eyebrow/index, and one primary
  action.
- `SectionRule`: label/index plus a stretching hairline.
- `ModuleCard`: module index, heading, optional action, content.
- `StatBlock`: label, mono value/unit, optional delta and context.
- `DataTable`: semantic table, sticky eyebrow header, aligned numeric cells,
  responsive overflow/row layout.
- `EmptyState`: serif headline, one explanatory sentence, one action, corner
  ticks.
- Base controls: button, labeled input/select, status badge, skeleton, inline
  error, and theme toggle.

Do not add chart, animation, or component-library dependencies until their
need is established. Existing data displays can use CSS/SVG rather than
introducing Recharts.

## Phase 1 implementation plan and approval gate

1. **Confirm framework scope before Phase 2.** The pasted brief names
   Next.js + TypeScript + Tailwind + shadcn, but the checked-in app is Vite +
   React JSX + custom CSS. A migration is a material architecture change and
   conflicts with “visual and interaction layer only” and “do not change
   routes/API/auth.” Recommended low-risk path: preserve the Vite app and
   translate the design tokens/primitives to CSS. Choosing Next.js would
   require explicit approval and a separately scoped migration.
2. Confirm whether the displayed brand remains **AthleteIQ** or changes to
   **AthliteIQ**.
3. If approved to proceed without a framework migration, implement tokens,
   theme toggle, shared primitives, signature treatments, and then refactor
   each route without changing APIs, routes, authentication, or assessment
   behavior.
4. Verify desktop 1440px, tablet 768px, mobile 375px, and wide 1920px in both
   themes, including loading, empty, error, long-table, keyboard-focus, and
   reduced-motion states. Capture screenshots after the implementation
   phase; no redesign screenshot is implied by this audit.

**No Phase 2 or application styling changes have been made.** Approval needed:
choose the existing Vite/CSS implementation path or explicitly authorize a
separately scoped Next.js migration, and confirm the product spelling.
