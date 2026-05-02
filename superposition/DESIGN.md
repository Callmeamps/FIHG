---
version: alpha
name: Superposition
description: A local-first developer command center. Dark workspace shell with monospace terminal surfaces and minimal chrome. The interface is a projection of backend state — precise, functional, zero decoration. No gradients, no shadows, no marketing polish. Every pixel earns its place.

colors:
  # --- Core surfaces ---
  canvas:       "#0c0c0e"   # page floor — near-black with a blue tinge
  surface:      "#131316"   # panel backgrounds
  surface-alt:  "#1a1a1f"   # alternating rows, nested panels
  raised:       "#22222a"   # hover states, selected items

  # --- Borders ---
  hairline:     "#2a2a33"   # default 1px dividers
  hairline-strong: "#3d3d4a" # emphasized separators

  # --- Text ---
  ink:          "#e8e8ed"   # primary text — warm white
  body:         "#9090a0"   # secondary text, metadata
  muted:        "#55556a"   # placeholders, disabled, timestamps
  inverse:      "#0c0c0e"   # text on light surfaces

  # --- Semantic: terminal ---
  term-bg:      "#090910"   # terminal panel floor — deepest black
  term-green:   "#4ade80"   # shell prompt, success
  term-yellow:  "#fbbf24"   # warnings, caution
  term-red:     "#f87171"   # errors, destructive
  term-blue:    "#60a5fa"   # links, info, paths
  term-cyan:    "#22d3ee"   # system output, metadata
  term-magenta: "#c084fc"   # agent output, special
  term-white:   "#d4d4d8"   # default output

  # --- Semantic: UI ---
  primary:      "#60a5fa"   # primary action — soft blue, not brandy
  success:      "#4ade80"   # done, idle, approved
  warning:      "#fbbf24"   # paused, pending, medium risk
  danger:       "#f87171"   # error, denied, cancelled, high risk
  info:         "#22d3ee"   # system messages, neutral highlights
  accent:       "#818cf8"   # selected state, active tab — indigo

  # --- Status badge backgrounds (tinted surfaces) ---
  status-done-bg:    "#0c1f14"   # green tint
  status-idle-bg:    "#0c1f14"
  status-paused-bg:  "#1a1408"   # yellow tint
  status-active-bg:  "#0f1729"   # blue tint
  status-error-bg:   "#1f0c0c"   # red tint

typography:
  # --- Font strategy ---
  # UI chrome: JetBrains Mono or Geist Mono — clean, readable at small sizes
  # Terminal: same monospace family, larger for output legibility
  # Fallback: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", monospace

  font-ui: "JetBrains Mono, Geist Mono, SF Mono, Cascadia Code, monospace"

  # --- Scale (monospace — sizes feel larger than px would suggest) ---
  xs:   11px    # timestamps, badge labels, fine print
  sm:   12px    # metadata, secondary labels, input labels
  base: 13px    # default body, list items, nav labels
  md:   14px    # panel titles, section headers
  lg:   16px    # modal titles, major headings
  xl:   20px    # page titles (rare — dashboard headline)
  mono: 13px    # terminal output — kept consistent with body

  # --- Weights (monospace families have narrow weight range) ---
  regular:  400   # default body
  medium:   500   # emphasized labels, nav items
  semibold: 600   # buttons, section titles

  # --- Letter spacing ---
  tight:    -0.02em   # display sizes feel tighter
  normal:   0          # body default
  wide:     0.06em    # uppercase labels, badges
  wider:    0.10em    # ALL CAPS button text

spacing:
  # Base unit: 4px
  xxs:  2px     # icon-to-label gap, dense lists
  xs:   4px     # within-component padding (badge padding)
  sm:   8px     # compact internal spacing
  md:   12px    # standard component padding
  lg:   16px    # panel padding, card internal
  xl:   24px    # section spacing, panel gaps
  xxl:  32px    # major section separation
  rail: 56px    # left rail width
  dock: 180px   # terminal dock default height

radius:
  none:   0px     # dominant — sharp corners throughout
  sm:     2px     # almost never used
  pill:   9999px  # status badges only

border:
  hairline: "1px solid {colors.hairline}"
  strong:   "1px solid {colors.hairline-strong}"
  active:   "1px solid {colors.accent}"

# --- Z-index scale ---
z:
  base:    0
  raised:  10    # hover states, tooltips
  panel:   20    # floating panels, dropdowns
  overlay: 30    # modals
  rail:    40    # left rail (always on top)
  toast:   50    # notifications

# --- Animation ---
motion:
  fast:    80ms   # hover states, color transitions
  normal:  150ms  # panel opens, tab switches
  slow:    250ms  # modal fade, large transitions

---

## Overview

Superposition is a developer workspace shell, not a marketing surface. The design inherits from terminal aesthetics and modern dev tooling (Warp, Zed, Linear, Arc) — precision over decoration.

**Key principles:**
1. **Monospace everywhere.** No proportional type. Everything is JetBrains Mono or equivalent. The monospace grid IS the aesthetic.
2. **Zero decoration.** No gradients, no shadows, no photography. Depth comes from surface contrast only.
3. **Surfaces over chrome.** UI recedes — the content (terminal output, task lists, chat) is the interface.
4. **Status is color.** Semantic colors are functional signals, not decoration.
5. **Sharp corners.** `{rounded.none}` everywhere. Badges get `{rounded.pill}`.

---

## Colors

### Core surfaces

| Token | Hex | Use |
|-------|-----|-----|
| `{colors.canvas}` | `#0c0c0e` | Page floor, deepest surfaces |
| `{colors.surface}` | `#131316` | Panel backgrounds, cards |
| `{colors.surface-alt}` | `#1a1a1f` | Alternating rows, nested panels |
| `{colors.raised}` | `#22222a` | Hover states, selected items, dropdowns |

### Borders

| Token | Hex | Use |
|-------|-----|-----|
| `{colors.hairline}` | `#2a2a33` | Default 1px dividers between sections |
| `{colors.hairline-strong}` | `#3d3d4a` | Emphasized separators, active borders |

### Text

| Token | Hex | Use |
|-------|-----|-----|
| `{colors.ink}` | `#e8e8ed` | Primary text — warm white |
| `{colors.body}` | `#9090a0` | Secondary text, metadata, labels |
| `{colors.muted}` | `#55556a` | Placeholders, disabled, timestamps |

### Terminal output colors

Terminal text uses semantic ANSI-inspired colors. These appear inside `RichTextLabel` output areas and should map directly to ANSI 256 color equivalents.

| Token | Hex | Use |
|-------|-----|-----|
| `{colors.term-green}` | `#4ade80` | Shell prompts (`$`), success output |
| `{colors.term-yellow}` | `#fbbf24` | Warnings (`warning:`, `caution:`) |
| `{colors.term-red}` | `#f87171` | Errors, stderr, failed commands |
| `{colors.term-blue}` | `#60a5fa` | URLs, paths, info links |
| `{colors.term-cyan}` | `#22d3ee` | System output, metadata, timestamps |
| `{colors.term-magenta}` | `#c084fc` | Agent output, special markers |
| `{colors.term-white}` | `#d4d4d8` | Default stdout |

### UI semantic colors

| Token | Hex | Use |
|-------|-----|-----|
| `{colors.primary}` | `#60a5fa` | Primary action buttons, links |
| `{colors.success}` | `#4ade80` | Done, idle, approved, active |
| `{colors.warning}` | `#fbbf24` | Paused, pending, medium risk |
| `{colors.danger}` | `#f87171` | Error, denied, cancelled, high risk |
| `{colors.info}` | `#22d3ee` | System messages, neutral highlights |
| `{colors.accent}` | `#818cf8` | Selected item, active tab indicator |

---

## Typography

**Font:** JetBrains Mono (or Geist Mono, SF Mono, Cascadia Code — same monospace family, no proportional type anywhere).

**No Serif. No Sans. Monospace only.**

### Type scale

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| `{typography.xs}` | 11px | 400 | Timestamps, badge labels, fine print |
| `{typography.sm}` | 12px | 400 | Metadata, secondary labels, input labels |
| `{typography.base}` | 13px | 400 | Default body, list items, nav labels |
| `{typography.md}` | 14px | 500 | Panel titles, section headers |
| `{typography.lg}` | 16px | 500 | Modal titles, major headings |
| `{typography.xl}` | 20px | 500 | Dashboard title (rare) |
| `{typography.mono}` | 13px | 400 | Terminal output — same as body |

### Principles
- All text is monospace. No size inflation for "hierarchy" — hierarchy comes from color, not size.
- `{colors.body}` at 13px is the workhorse. `{colors.ink}` at 13px is emphasized. Use color, not size, to signal importance.
- Uppercase with `{typography.wide}` letter-spacing (0.06em) for: section labels, status badges, button text.
- All-caps with `{typography.wider}` letter-spacing (0.10em) for: button labels only.

---

## Layout

### Structure

```
┌────────────┬─────────────────────────────────┬────────────┐
│  LEFT RAIL │        CENTER VIEWPORT          │  INSPECTOR │
│   (56px)   │         (flexible)             │   (15%)    │
│            │                                 │            │
│  Dashboard │   active panel replaces here     │  metadata  │
│  Projects  │                                 │  on selected│
│  Chatbooks │                                 │  item      │
│  Activity  │                                 │            │
│  Agents    │                                 │            │
│            ├─────────────────────────────────┤            │
│            │       TERMINAL DOCK (180px)      │            │
│            │   always visible, bottom         │            │
└────────────┴─────────────────────────────────┴────────────┘
```

- **Left rail:** 56px wide, fixed. Icon + label (hidden label by default). Expands on hover or shows tooltip.
- **Center viewport:** Fills remaining width. One panel at a time — `queue_free()` old before adding new.
- **Inspector:** 15% viewport width, right side. Always mounted — shows "(no selection)" until populated. Never hides.
- **Terminal dock:** Fixed 180px height, bottom 30% of center area. Always running session. Can be toggled minimized.
- **No modals by default.** Panels handle inline editing. Modals only for: confirm destructive, settings.

### Responsive strategy
- Below 900px: inspector hides, terminal dock collapses to icon in rail
- Below 600px: left rail collapses to icon-only (no labels)
- Terminal dock never hides completely — it's the spine

---

## Elevation & Depth

Depth is surface-only. No shadows, no glows, no gradients.

| Level | Treatment | Use |
|-------|----------|-----|
| `{colors.canvas}` | Page floor | Body background |
| `{colors.surface}` | Panel background | Cards, list containers, terminal frame |
| `{colors.surface-alt}` | Alternating | Table rows, nested panels |
| `{colors.raised}` | Hover / selected | Row hover, dropdown backgrounds |

1px hairline borders (`{colors.hairline}`) separate panels from the canvas. Active panels get `{colors.accent}` border on their active edge.

---

## Shapes

`{rounded.none}` (0px) everywhere without exception.

The only permitted rounded surface is **status badges** — `{rounded.pill}` (9999px). They read as labels, not buttons.

No rounded buttons. No rounded cards. No rounded inputs. Sharp corners are the workspace aesthetic.

---

## Components

### Rail Button

**`rail-button`** — Left rail navigation item.

```
backgroundColor: transparent
textColor: {colors.body}           // inactive
textColor: {colors.ink}            // active/hover
typography: {typography.base}      // 13px
letterSpacing: {typography.wide}  // 0.06em uppercase
padding: 12px 16px
height: 40px
width: 56px collapsed, auto expanded
border: none
```

Active state: left 2px border in `{colors.accent}`, text becomes `{colors.ink}`.

**`rail-button-active`**: adds `border-left: 2px solid {colors.accent}`, text `{colors.ink}`.

### Panel Header

**`panel-header`** — Section title inside a panel.

```
backgroundColor: {colors.surface}
textColor: {colors.body}
typography: {typography.md}        // 14px / 500
letterSpacing: {typography.wide}   // 0.06em uppercase
padding: 8px 12px
borderBottom: {border.hairline}
```

No bottom margin — header is flush with panel content.

### Text Input

**`text-input`** — Single-line input field.

```
backgroundColor: {colors.term-bg}  // deepest black — feels like terminal
textColor: {colors.ink}
typography: {typography.base}
border: {border.hairline}
rounded: {rounded.none}
padding: 8px 12px
height: 36px
caretColor: {colors.primary}
```

Focus state: border becomes `{border.active}` (`{colors.accent}` 1px).

### Primary Button

**`button-primary`** — Main action trigger.

```
backgroundColor: {colors.primary}   // soft blue
textColor: {colors.inverse}        // dark text on light button
typography: {typography.base}      // 13px
fontWeight: {typography.semibold} // 600
letterSpacing: {typography.wider} // 0.10em uppercase
rounded: {rounded.none}
padding: 0 16px
height: 36px
border: none
```

**`button-danger`**: background `{colors.danger}`, text white.

**`button-ghost`**: background transparent, border `{border.hairline}`, text `{colors.body}`.

### Status Badge

**`badge`** — Inline status indicator.

```
backgroundColor: (semantic tint — see below)
textColor: (semantic — matches badge color)
typography: {typography.xs}
letterSpacing: {typography.wide}
rounded: {rounded.pill}
padding: 2px 8px
border: none
```

Status→color mapping:

| Status | Text color | Background |
|--------|-----------|------------|
| idle, done, approved | `{colors.success}` | `{colors.status-done-bg}` |
| active, running, in_progress | `{colors.primary}` | `{colors.status-active-bg}` |
| paused, pending, waiting | `{colors.warning}` | `{colors.status-paused-bg}` |
| cancelled, denied, error, failed | `{colors.danger}` | `{colors.status-error-bg}` |

### List Item

**`list-item`** — Clickable row in a list (projects, tasks, agents).

```
backgroundColor: transparent
textColor: {colors.ink}
hover: backgroundColor {colors.raised}
typography: {typography.base}
padding: 10px 12px
borderBottom: {border.hairline}
```

Selected list item: `backgroundColor: {colors.raised}`, left 2px border in `{colors.accent}`.

### Property Row

**`prop-row`** — Key/value pair in inspector panel.

```
keyColor: {colors.muted}
keyTypography: {typography.sm}
valueColor: {colors.body}
valueTypography: {typography.base}
padding: 4px 0
separator: none
```

Priority keys (id, title, name, status) get `{colors.ink}` color for the value. IDs are displayed truncated (first 8 chars) with full ID on hover tooltip.

### Terminal Output Line

**`term-line`** — Single line of terminal output (RichTextLabel).

```
typography: {typography.mono}      // 13px monospace
defaultColor: {colors.term-white}
padding: 0 12px
lineHeight: 1.5
```

ANSI color mapping in RichTextLabel BBCode:
- `[color=#4ade80]` → prompt, success
- `[color=#fbbf24]` → warnings
- `[color=#f87171]` → errors, stderr
- `[color=#60a5fa]` → paths, links
- `[color=#22d3ee]` → metadata, system
- `[color=#c084fc]` → agent output

Command echo: `{colors.term-yellow}` + bold. Output: `{colors.term-white}`. Errors: `{colors.term-red}`.

### Activity Feed Row

**`feed-row`** — Single event in the activity/inspector feed.

```
timestampColor: {colors.muted}
eventColor: (per-event-type — see badge colors)
entityTypeColor: {colors.body}
detailColor: {colors.muted}
typography: {typography.sm}
padding: 6px 12px
borderBottom: {border.hairline}
```

Event type gets color-coded badge (same as status badges, color per event namespace):
- `task.*` → `{colors.term-blue}`
- `agent.*` → `{colors.term-magenta}`
- `approval.*` → `{colors.term-yellow}`
- `project.*` → `{colors.term-green}`
- `run.*` → `{colors.term-cyan}`

### Panel Container

**`panel`** — Wrapper for any centered viewport panel (projects list, chatbook, etc.).

```
backgroundColor: {colors.surface}
borderLeft: {border.hairline}
borderRight: {border.hairline}
borderTop: none
padding: 0
minHeight: 100%
```

Panels don't have rounded corners or shadows. The surface + border IS the panel.

### Toast / Notification

**`toast`** — Ephemeral feedback message.

```
backgroundColor: {colors.raised}
border: {border.hairline-strong}
textColor: {colors.ink}
typography: {typography.sm}
rounded: {rounded.none}
padding: 12px 16px
z-index: {z.toast}
```

Error toasts get left 2px border in `{colors.danger}`. Success toasts get `{colors.success}`. Auto-dismiss after 3s, stack from bottom-right.

---

## Do's and Don'ts

### Do
- Use monospace everywhere — JetBrains Mono or equivalent. No proportional type.
- Use `{colors.body}` as the default text color. `{colors.ink}` only for primary content.
- Use status badge colors semantically — green = good/done, red = error/critical, yellow = warning/pending, blue = active/info.
- Keep padding tight: `{spacing.lg}` (16px) for panels, `{spacing.md}` (12px) for list items.
- Use `{rounded.none}` everywhere. Pill badges only.
- Apply `{typography.wide}` (0.06em) letter-spacing to: section labels, status badges, nav items.
- Apply `{typography.wider}` (0.10em) letter-spacing to: button text only.

### Don't
- Don't use shadows, glows, or gradients for depth.
- Don't use rounded corners on anything except status badges.
- Don't use bold text (weight 600+) for body content — 400 everywhere, 600 for emphasis only.
- Don't use `{colors.ink}` for secondary text — it defeats the hierarchy.
- Don't use rounded buttons. Sharp rectangles only.
- Don't mix proportional and monospace type in the same component.
- Don't add decorative elements (icons purely for decoration, colored dividers that aren't functional).
- Don't use the accent color (`{colors.accent}`) for large surfaces — it's a border/indicator only.

---

## Panel-Specific Guidance

### Dashboard
- Single-column layout, top-to-bottom: status strip (health + counts) → recent projects → running terminals → pending approvals.
- Each section is a `panel-header` + list. No card grid.
- Stats use `spec-cell`-style display: large `{typography.lg}` number + `{typography.xs}` label below.

### Projects
- List view: `list-item` per project. Click → inspector populates + optional panel slide-in for tasks.
- Create: inline form at top of list. `text-input` + `button-primary`.
- No card grid. No thumbnail. Just text + status badge.

### Chatbooks
- Message list: `term-line` colored by role. `[user]` in `{colors.term-blue}`, `[assistant]` in `{colors.term-magenta}`, `[system]` in `{colors.muted}`.
- Input: `text-input` full-width at bottom, `button-primary` ("Send") right-aligned.
- No bubble design — flat text with role prefix.

### Activity
- Feed of `feed-row` items, newest-first.
- Filter bar above: `text-input` (event search) + `OptionButton` (entity type).
- Scrollable feed area. Auto-scroll to bottom on new entries.

### Terminal
- Background: `{colors.term-bg}` (#090910) — deepest surface.
- Output: `RichTextLabel` with `scroll_following = true`.
- Input: `text-input` at bottom of panel, no visible send button (Enter to submit).
- Session ID shown top-right as `{typography.xs}` `{colors.muted}` label.

### Inspector
- Always visible. Default: "(no selection)" in `{colors.muted}`.
- Populated via `main.inspect(type, id)` call from any panel.
- `prop-row` list sorted: priority keys first (id, title/name, status, created_at), rest alphabetical.

### Agents
- Same list view pattern as Projects.
- Status badge shows agent status (idle, busy, paused).
- `mode` displayed as text label in `{colors.body}`.

---

## Status → Color Reference

All status values and their corresponding badge + text colors:

| Status value | Badge bg | Text color |
|-------------|----------|------------|
| idle, done, approved | `status-done-bg` | `success` |
| active, running, in_progress | `status-active-bg` | `primary` |
| paused, pending, waiting | `status-paused-bg` | `warning` |
| cancelled, denied, error, failed | `status-error-bg` | `danger` |
| pending (approval) | `status-paused-bg` | `warning` |

---

## Implementation Notes

- Export tokens as a Godot `Resource` or static class so scenes can reference `{Token.canvas}` instead of hardcoded hex values.
- Terminal `RichTextLabel` uses BBCode for color: `[color=#4ade80]text[/color]`.
- All `@onready` node references should use `%NodeName` syntax (node path from scene root).
- Panel transitions: `modulate` fade, 150ms. Old panel fades out (100ms), new fades in (150ms).
- Hover states on all interactive elements — `backgroundColor` → `{colors.raised}`.
- `focus_mode` enabled on all `LineEdit` and `TextEdit` nodes.
- No custom fonts beyond JetBrains Mono — use Godot's built-in fallback chain.