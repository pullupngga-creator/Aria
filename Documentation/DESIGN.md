# Aria — UI/UX Design System

## Design Philosophy
**Soft Digital Luxury × High-Focus Minimalism**

Aria rejects clinical white screens and generic dark themes. The interface is engineered as a premium thinking environment—calm, focused, and quietly powerful. Every pixel serves cognition.

---

## Color Palette

### Primary Surfaces
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-obsidian` | `#111214` | Primary sidebar (Sources Vault) background |
| `--bg-anthracite` | `#1A1B1E` | Main chat canvas background |
| `--bg-elevated` | `#1E1F23` | Elevated cards, dropdowns, modals |
| `--bg-hover` | `#25262B` | Hover states on list items |
| `--bg-active` | `#2A2B2F` | Active/selected item backgrounds |

### Borders & Dividers
| Token | Hex | Usage |
|-------|-----|-------|
| `--border-hairline` | `#2A2B2F` | Panel dividers, list separators |
| `--border-focus` | `#4D90FE` | Focus rings, active borders |
| `--border-subtle` | `#3A3B3F` | Subtle card borders |

### Typography
| Token | Hex | Usage |
|-------|-----|-------|
| `--text-primary` | `#E8E8EC` | Headings, primary content |
| `--text-secondary` | `#9CA3AF` | Metadata, timestamps, hints |
| `--text-muted` | `#6B7280` | Placeholders, disabled states |
| `--text-inverse` | `#111214` | Text on accent backgrounds |

### Accent System
| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-electric` | `#4D90FE` | Primary actions, active states, @-mention chips |
| `--accent-electric-glow` | `rgba(77, 144, 254, 0.15)` | Soft glow behind active sources |
| `--accent-success` | `#22C55E` | Upload complete, success states |
| `--accent-warning` | `#F59E0B` | Token limit warnings |
| `--accent-error` | `#EF4444` | API errors, parse failures |

---

## Typography System

### Font Family
- **Primary**: `Inter` or `Geist` (geometric sans-serif)
- **Monospace**: `JetBrains Mono` or `Geist Mono` (code blocks, metadata)

### Scale
| Level | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| Display | `28px` | 600 | 1.2 | Empty state headings |
| H1 | `20px` | 600 | 1.3 | Panel titles |
| H2 | `16px` | 500 | 1.4 | Section headers |
| Body | `14px` | 400 | 1.4 | Chat messages, descriptions |
| Small | `12px` | 400 | 1.4 | Metadata, timestamps |
| Micro | `11px` | 500 | 1.3 | Badges, counters |

---

## Component Specifications

### Sources Vault (Left Panel — 320px fixed)
- **Header**: "Sources Vault" title + upload button (electric blue, 32px icon)
- **File List**: Scrollable, virtualized list of document rows
  - Each row: Icon (24px) | Filename (truncated) | Word count (muted) | Glow dot (active)
  - Hover: `--bg-hover` background transition (150ms ease)
  - Active: Left border 3px `--accent-electric` + `--accent-electric-glow` background
- **Empty State**: Centered icon + "Drop files to begin" + supported formats list
- **Search Bar**: Sticky top, 40px height, `--bg-elevated` background, magnifying glass icon

### Chat Canvas (Right Panel — Fluid)
- **Header**: Conversation title (editable inline) | Model selector | New chat button
- **Message Thread**: Reverse-scroll (newest at bottom), 24px gap between messages
  - **User Message**: Right-aligned, `--bg-elevated` bubble, max-width 80%
  - **AI Message**: Left-aligned, full-width, markdown-rendered
  - **Timestamp**: Micro text below each message
  - **Actions Row**: Copy, regenerate, delete icons (appear on hover, 200ms fade)
- **Empty State**: Centered logo mark + tagline + quick-start prompts (clickable chips)
- **Input Bar**: Fixed bottom, 56px min-height, auto-expand to 200px
  - `--bg-elevated` background, `--border-hairline` top border
  - @-mention chips: `--accent-electric` background, rounded 6px, removable via ×
  - Send button: Electric blue circle, 36px, paper airplane icon

### @-Mention Dropdown
- **Trigger**: `@` character in input
- **Position**: Absolute, above input bar, max-height 240px
- **Row**: File icon | Filename (highlighted match) | Content preview (truncated, 40 chars)
- **Navigation**: Arrow keys + Enter to select, Escape to close
- **Styling**: `--bg-elevated` background, 8px border-radius, subtle shadow

### Toast Notifications
- **Position**: Bottom-right, stacked
- **Style**: `--bg-elevated` background, left border 3px colored by type
- **Duration**: 4 seconds, auto-dismiss with 300ms fade-out

---

## Micro-Interactions

| Interaction | Spec |
|-------------|------|
| Source activation glow | `box-shadow: 0 0 20px var(--accent-electric-glow)` |
| List item hover | `background-color` transition 150ms `ease-out` |
| Message appear | `opacity: 0→1`, `translateY: 8px→0`, 200ms `ease-out` |
| Send button press | `scale: 0.95` on mousedown, 100ms |
| @-mention dropdown | `opacity: 0→1`, `translateY: 4px→0`, 150ms |
| Toast slide-in | `translateX: 100%→0`, 300ms `cubic-bezier(0.16, 1, 0.3, 1)` |
| Panel resize | Real-time 1px divider drag, cursor `col-resize` |

---

## Layout Grid
- **Panel Divider**: 1px `--border-hairline`, draggable (min 240px, max 480px for left panel)
- **Border Radius**: 8px (cards), 6px (buttons/chips), 4px (inputs)
- **Spacing Scale**: 4px base (4, 8, 12, 16, 24, 32, 48)
- **Shadows**: None (flat luxury aesthetic), except dropdowns: `0 8px 24px rgba(0,0,0,0.4)`
