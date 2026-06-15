"""Design system tokens for Aria UI."""

from typing import Final, TypedDict

import flet as ft

# Color Palette from DESIGN.md
COLORS: Final[dict[str, str]] = {
    # Primary Surfaces
    "bg_obsidian": "#111214",
    "bg_anthracite": "#1A1B1E",
    "bg_elevated": "#1E1F23",
    "bg_hover": "#25262B",
    "bg_active": "#2A2B2F",
    # Borders & Dividers
    "border_hairline": "#2A2B2F",
    "border_focus": "#4D90FE",
    "border_subtle": "#3A3B3F",
    # Typography
    "text_primary": "#E8E8EC",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "text_inverse": "#111214",
    # Accent System
    "accent_electric": "#4D90FE",
    "accent_electric_glow": "rgba(77, 144, 254, 0.15)",
    "accent_success": "#22C55E",
    "accent_warning": "#F59E0B",
    "accent_error": "#EF4444",
}


class TypographyToken(TypedDict):
    size: float
    weight: int
    height: float


# Typography Scale from DESIGN.md
TYPOGRAPHY: Final[dict[str, TypographyToken]] = {
    "display": {"size": 28, "weight": 600, "height": 1.2},
    "h1": {"size": 20, "weight": 600, "height": 1.3},
    "h2": {"size": 16, "weight": 500, "height": 1.4},
    "body": {"size": 14, "weight": 400, "height": 1.4},
    "small": {"size": 12, "weight": 400, "height": 1.4},
    "micro": {"size": 11, "weight": 500, "height": 1.3},
}

# Font Families
FONT_FAMILY_PRIMARY: Final[str] = "Geist"
FONT_FAMILY_MONO: Final[str] = "JetBrains Mono"


def build_theme() -> ft.Theme:
    """Build a Flet Theme from the Aria design token maps.

    Wires COLORS and TYPOGRAPHY into ColorScheme and TextTheme so every
    Flet widget inherits the correct values without per-widget overrides.
    """
    return ft.Theme(
        font_family=FONT_FAMILY_PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=COLORS["accent_electric"],
            on_primary=COLORS["text_inverse"],
            primary_container=COLORS["bg_active"],
            secondary=COLORS["accent_electric"],
            surface=COLORS["bg_elevated"],
            on_surface=COLORS["text_primary"],
            on_surface_variant=COLORS["text_secondary"],
            outline=COLORS["border_hairline"],
            outline_variant=COLORS["border_subtle"],
            error=COLORS["accent_error"],
            on_error=COLORS["text_inverse"],
        ),
        text_theme=ft.TextTheme(
            # Display — empty-state headings (28px / 600)
            display_large=ft.TextStyle(
                size=TYPOGRAPHY["display"]["size"],
                weight=ft.FontWeight.W_600,
            ),
            # H1 — panel titles (20px / 600)
            title_large=ft.TextStyle(
                size=TYPOGRAPHY["h1"]["size"],
                weight=ft.FontWeight.W_600,
            ),
            # H2 — section headers (16px / 500)
            title_medium=ft.TextStyle(
                size=TYPOGRAPHY["h2"]["size"],
                weight=ft.FontWeight.W_500,
            ),
            # Body — chat messages, descriptions (14px / 400)
            body_large=ft.TextStyle(
                size=TYPOGRAPHY["body"]["size"],
                weight=ft.FontWeight.W_400,
            ),
            # Small — metadata, timestamps (12px / 400)
            body_small=ft.TextStyle(
                size=TYPOGRAPHY["small"]["size"],
                weight=ft.FontWeight.W_400,
            ),
            # Micro — badges, counters (11px / 500)
            label_small=ft.TextStyle(
                size=TYPOGRAPHY["micro"]["size"],
                weight=ft.FontWeight.W_500,
            ),
        ),
    )
