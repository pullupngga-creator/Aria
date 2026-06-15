---
name: Aria
colors:
  surface: '#111316'
  surface-dim: '#111316'
  surface-bright: '#37393c'
  surface-container-lowest: '#0c0e11'
  surface-container-low: '#1a1c1f'
  surface-container: '#1e2023'
  surface-container-high: '#282a2d'
  surface-container-highest: '#333538'
  on-surface: '#e2e2e6'
  on-surface-variant: '#c2c6d5'
  inverse-surface: '#e2e2e6'
  inverse-on-surface: '#2f3034'
  outline: '#8c909f'
  outline-variant: '#424753'
  surface-tint: '#acc7ff'
  primary: '#acc7ff'
  on-primary: '#002f68'
  primary-container: '#4d90fe'
  on-primary-container: '#00295d'
  inverse-primary: '#005bbf'
  secondary: '#c7c6ca'
  on-secondary: '#2f3033'
  secondary-container: '#48494c'
  on-secondary-container: '#b9b8bc'
  tertiary: '#c7c6c9'
  on-tertiary: '#303032'
  tertiary-container: '#929294'
  on-tertiary-container: '#2a2b2d'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d7e2ff'
  primary-fixed-dim: '#acc7ff'
  on-primary-fixed: '#001a40'
  on-primary-fixed-variant: '#004492'
  secondary-fixed: '#e3e2e6'
  secondary-fixed-dim: '#c7c6ca'
  on-secondary-fixed: '#1a1b1e'
  on-secondary-fixed-variant: '#46474a'
  tertiary-fixed: '#e3e2e4'
  tertiary-fixed-dim: '#c7c6c9'
  on-tertiary-fixed: '#1b1c1e'
  on-tertiary-fixed-variant: '#464749'
  background: '#111316'
  on-background: '#e2e2e6'
  surface-variant: '#333538'
  bg-elevated: '#1E1F23'
  bg-hover: '#25262B'
  bg-active: '#2A2B2F'
  border-hairline: '#2A2B2F'
  border-subtle: '#3A3B3F'
  text-secondary: '#9CA3AF'
  text-muted: '#6B7280'
  accent-success: '#22C55E'
  accent-warning: '#F59E0B'
  accent-error: '#EF4444'
  glow-electric: rgba(77, 144, 254, 0.15)
typography:
  display:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '500'
    lineHeight: '1.4'
  body:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.4'
  metadata:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  badge:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: 0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  vault-width: 320px
  gutter: 24px
---

## Brand & Style

The design system is built upon the philosophy of **Soft Digital Luxury x High-Focus Minimalism**. It treats the interface not as a utility, but as a premium cognitive environment—a "laboratory for thought." The aesthetic rejects the clinical harshness of standard dark modes in favor of deep, tonal layering and atmospheric "glow" states that signify activity and intelligence.

The visual direction combines:
- **Minimalism:** Aggressive reduction of non-essential UI chrome to prioritize content and cognition.
- **Tonal Layering:** Using distinct dark neutrals (Obsidian and Anthracite) to define functional zones without relying on heavy borders.
- **High-Focus Accents:** Utilizing Electric Blue specifically for "active context" and primary actions, creating a clear mental model of what the AI is currently "thinking" about.
- **Technical Precision:** Subtle nods to developer-centric tools through monospaced metadata, providing a sense of transparency and accuracy.

## Colors

This design system utilizes a sophisticated dark-themed palette designed for prolonged deep work sessions. 

### Surface Strategy
- **Base (Vault):** `#111214` (Obsidian) provides the deepest foundation for the sidebar, grounding the source library.
- **Canvas (Work Area):** `#1A1B1E` (Anthracite) offers a slightly lifted surface for the primary chat and document interaction, reducing eye strain.
- **Elevation:** `#1E1F23` is reserved for floating elements like modals and cards, creating a clear hierarchy of interaction.

### Meaningful Accents
The primary accent, **Electric Blue**, is more than a brand color; it represents "binding." When a document or text string is highlighted in this blue or accompanied by the electric glow, it indicates active inclusion in the AI's cognitive context. Success, warning, and error states are used sparingly to maintain the "quiet" nature of the workspace.

## Typography

The typography system prioritizes clarity and structural hierarchy. 

- **Primary Typeface:** **Geist** provides a modern, geometric clarity that feels technical yet premium. It is used for all narrative and structural content.
- **Secondary Typeface:** **JetBrains Mono** is utilized for metadata, timestamps, badges, and code. This creates a clear visual distinction between "the conversation" and "the data."
- **Readability:** A generous line-height (1.4) is applied to body text to ensure high legibility during long research sessions. 
- **Hierarchy:** Use `display` only for empty states. `H1` is reserved for panel titles, while `metadata` is the workhorse for all auxiliary information.

## Layout & Spacing

This design system follows a **Fixed-to-Fluid** desktop-first model.

### Grid & Panels
- **Sources Vault:** A fixed 320px left-hand panel that serves as the permanent anchor for document management.
- **Chat Canvas:** A fluid central area that expands to fill the remaining horizontal space, optimized for reading markdown-heavy responses.
- **Dividers:** Use 1px hairline borders (`--border-hairline`) to separate panels. The vault/canvas divider should be draggable, with a cursor change to `col-resize`.

### Spacing Rhythm
A 4px base unit drives all layout decisions. Margins within the Chat Canvas should remain generous (24px to 32px) to prevent the UI from feeling cramped. The vertical gap between distinct message blocks is set to 24px to maintain clear conversational boundaries.

## Elevation & Depth

In this design system, depth is communicated through **Tonal Tiering** and **Atmospheric Glow** rather than traditional drop shadows.

- **Stacking Order:**
  1. `bg-obsidian`: Level 0 (The Vault foundation).
  2. `bg-anthracite`: Level 1 (The interaction canvas).
  3. `bg-elevated`: Level 2 (Message bubbles, inputs, and cards).
- **The Glow Effect:** Active states for sources and mention-chips utilize a `0 0 20px` soft glow in the accent color at 15% opacity. This creates a "backlit" feel, suggesting digital luxury.
- **Shadow Exceptions:** To ensure legibility, floating menus and `@-mention` dropdowns are the only elements to receive a traditional high-diffusion shadow: `0 8px 24px rgba(0,0,0,0.4)`.

## Shapes

The shape language is controlled and systematic, moving from sharper to softer corners based on the element's complexity and function.

- **Cards & Modals:** 8px (`rounded-lg`) for a soft, approachable container.
- **Buttons & Mention Chips:** 6px for a precise, "clickable" appearance.
- **Inputs:** 4px for a structured, utilitarian feel.
- **Status Dots:** 100% (circular) for the "active context" indicators found in the file list.

This progression ensures that interaction elements feel distinct from structural containers.

## Components

### Buttons & Primary Actions
- **Add Source:** A high-contrast button utilizing the Electric Blue background with `--text-inverse`.
- **Icon Buttons:** Use 20px icons within a 32px or 36px hit area. On hover, apply `--bg-hover` with a 150ms ease.

### Message Bubbles
- **User Messages:** Right-aligned, utilizing `--bg-elevated` with a max-width of 80%. 
- **AI Messages:** Left-aligned, no background container, full-width to allow markdown (tables, lists, code) to breathe.

### Input Bar & Mentions
- **Input:** A fixed-bottom bar that expands vertically. Use `--bg-elevated` with a top border.
- **@-Mention Chips:** Rounded 6px, Electric Blue background, with a small "x" for removal. When the `@` trigger is active, the dropdown should appear directly above the input.

### Sources Vault Rows
- **List Items:** 150ms transition on hover to `--bg-hover`.
- **Active State:** When a source is "bound" to context, show a 3px left border of Electric Blue and apply the soft glow effect to the row background.

### Notifications & Toasts
- **Style:** Flat, `--bg-elevated` surfaces with a 3px colored accent border on the left to denote type (Success, Warning, Error). Position in the bottom-right of the viewport.