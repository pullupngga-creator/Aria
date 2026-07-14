# DESIGN.md — Aria UI/UX

## Design Philosophy: "Fluent Locality"
A calm, breathable interface that feels native to the OS while maintaining a modern SaaS clarity. The aesthetic emphasizes spatial awareness — you are always aware of your local network context. The interface is light by default (to contrast with typical dark messaging apps) but supports a refined dark mode. Airy spacing, subtle motion, and tactile feedback make the zero-config experience feel effortless.

## Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--aria-bg-primary` | `#F7F8FA` | Main app background (soft off-white) |
| `--aria-bg-secondary` | `#FFFFFF` | Panels, cards, sidebar |
| `--aria-bg-tertiary` | `#F0F1F5` | Elevated surfaces, hover states, input backgrounds |
| `--aria-surface` | `#E8EAF0` | Secondary buttons, tags, inactive tabs |
| `--aria-border` | `#D8DCE6` | Subtle dividers, hairlines |
| `--aria-border-hover` | `#C4C9D4` | Active borders, focus rings |
| `--aria-text-primary` | `#1A1D26` | Headings, primary text |
| `--aria-text-secondary` | `#5E6270` | Body text, secondary labels |
| `--aria-text-muted` | `#9AA0B0` | Placeholders, timestamps, disabled |
| `--aria-accent` | `#4F7DF3` | Primary actions, active peer indicator, send button |
| `--aria-accent-hover` | `#3B66D9` | Accent hover |
| `--aria-accent-glow` | `rgba(79, 125, 243, 0.12)` | Soft glow on active elements |
| `--aria-success` | `#34C759` | Online status, delivered receipts, trusted peer |
| `--aria-warning` | `#FF9500` | Untrusted peer, pending approval |
| `--aria-error` | `#FF3B30` | Errors, blocked peer, transfer failed |
| `--aria-voice` | `#AF52DE` | Voice message accents, recording indicator |

### Dark Mode
| Token | Hex | Usage |
|-------|-----|-------|
| `--aria-dark-bg` | `#12131A` | Main background |
| `--aria-dark-surface` | `#1C1E26` | Panels |
| `--aria-dark-elevated` | `#252730` | Inputs, hover |
| `--aria-dark-border` | `#2E303A` | Dividers |
| `--aria-dark-text` | `#E8EAF0` | Primary text |
| `--aria-dark-muted` | `#7A7E8C` | Secondary text |

## Typography
- **Font Family**: `Inter` (weights 400, 500, 600) + `JetBrains Mono` for code/timestamps
- **Scale**: 11px (timestamps) → 13px (body) → 15px (UI labels) → 20px (headings)
- **Line Height**: 1.5 for chat bubbles, 1.3 for UI labels
- **Chat Messages**: 15px / 1.5 / 400 weight for maximum readability

## Visual Language

### Spatial Layout
- **Three-pane layout**: Sidebar (peers) → Thread List (active chats) → Active Thread (conversation)
- Collapsible sidebar on narrow windows (< 900px)
- Thread view is the dominant spatial zone (60% width)

### Depth & Elevation
- No heavy shadows. Use layered borders and subtle background shifts.
- Active chat thread: `background: var(--aria-bg-secondary)` with 1px border separator
- Chat bubbles: flat with slight background tint; no border-radius asymmetry (8px all corners, 2px on message-tail side)

### Radius
- Small (buttons, inputs, badges): `15px`
- Medium (cards, panels, modals): `20px`
- Large (main containers, avatar frames): `25px`
- Full (avatars, status dots): `9999px`

### Animations
- **Transitions**: `all 0.15s ease-out` for UI; `transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)` for panels
- **Peer discovery**: Staggered fade-in (50ms delay per item) when peer list populates
- **Message send**: Subtle scale-down (0.98 → 1.0) + fade-in on new message bubble
- **File transfer**: Progress bar with smooth width transition + pulsing glow on active transfer
- **Recording**: Red pulsing ring around record button (CSS animation)
- **Typing indicator**: Three-dot bounce animation (CSS keyframes)

## Component Library

### Vanilla JS Component Architecture
Aria uses a lightweight custom component system (no React/Vue). Components are ES6 classes or factory functions that mount to DOM nodes.

#### Core Components
- `AriaSidebar` — Peer list with search, online status, trust badges
- `AriaThreadList` — Active conversation list with last message preview
- `AriaChatView` — Message thread with scroll anchoring, lazy load history
- `AriaMessageBubble` — Text, file, or voice message renderer
- `AriaFileTransfer` — Progress overlay + inline file card
- `AriaVoiceRecorder` — Record button + waveform preview + send/cancel
- `AriaInputBar` — Text input + attachment + voice toggle
- `AriaPeerCard` — Peer identity card with fingerprint, trust actions
- `AriaModal` — Settings, peer details, file preview
- `AriaToast` — OS-native notification wrapper + in-app toast stack
- `AriaEmptyState` — Illustration + copy for zero-peers, zero-messages

#### Styling Approach
- **Tailwind CSS v4** via CDN or bundled build step for utility classes
- **CSS Custom Properties** for all theme tokens (light/dark toggle via `data-theme` attribute on `<html>`)
- **BEM-like naming** for component-specific styles: `.aria-chat__bubble`, `.aria-sidebar__peer`
- No inline styles except dynamic values (progress widths, waveform heights)

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Title Bar (native Tauri: traffic lights + "Aria" + network status indicator) │
├──────────┬──────────────┬─────────────────────────────────────────────────────┤
│          │              │                                                     │
│ Sidebar  │ Thread List  │              Active Chat Thread                     │
│ (Peers)  │ (Chats)      │                                                     │
│ 200px    │ 280px        │              (Messages + Input Bar)                 │
│          │              │                                                     │
│          │              │                                                     │
├──────────┴──────────────┴─────────────────────────────────────────────────────┤
│  Status Bar (Network: Online | Peers: 4 | Transfer: 12 MB/s)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Sidebar**: Peer list with search filter, online/offline grouping, trust indicators
- **Thread List**: Chronological list of active conversations; shows last message snippet + timestamp
- **Active Thread**: Full message history, scrollable, anchored to bottom; input bar fixed at bottom
- **Status Bar**: Network interface name, peer count, active transfer throughput

## Responsive Behavior
- **Desktop**: Full three-pane layout
- **Narrow (< 900px)**: Sidebar collapses to icon rail (64px); thread list overlays or slides
- **Very narrow (< 600px)**: Single-pane navigation; thread list and chat view are separate "screens" with back button

## Iconography
- **Library**: `lucide` (vanilla JS, loaded as SVG sprite or inline)
- **Style**: 1.5px stroke, 16px default for UI, 20px for empty states
- **Color**: Inherit from CSS currentColor
