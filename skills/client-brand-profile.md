---
name: client-brand-profile
description: >
  Multi-client brand identity management for autonomous AI agents. Use BEFORE generating
  any marketing asset (images, videos, pitch decks, social posts, ads). This skill teaches
  agents to learn a client's brand first — colors, fonts, voice, logo, audience, style —
  then stores the profile as structured JSON for all downstream skills to consume. Supports
  onboarding new clients, updating existing profiles, and routing asset generation to the
  correct brand. Required dependency for image-generation-agent, video-ad-generation, and
  pitch-deck-generation skills.
metadata:
  author: localcomm
  version: '1.0'
  updated: '2026-03-15'
---

# Client Brand Profile — Multi-Client Brand Intelligence

## When to Use This Skill

Use this skill BEFORE any creative asset generation when:

- Onboarding a new client (restaurant, business, etc.)
- Generating images, videos, or pitch decks for a specific client
- The agent needs to know which brand colors, logo, fonts, tone to use
- Switching between multiple clients in a pipeline
- Updating or evolving a client's brand identity

## Core Concept: Brand-First Generation

Every asset generation skill (image, video, pitch deck) MUST load the client's brand
profile before producing anything. The profile is the single source of truth for:

- Visual identity (colors, fonts, logo, photography style)
- Voice and tone (formal, casual, playful, authoritative)
- Business context (industry, audience, competitors, USPs)
- Platform preferences (which social platforms, posting frequency)
- Asset history (what's been generated before, what performed well)

## Brand Profile JSON Schema

```json
{
  "schema_version": "1.0",
  "client_id": "marios-bistro",
  "business_name": "Mario's Bistro",
  "legal_name": "Mario's Bistro LLC",
  "industry": "restaurant",
  "industry_sub": "italian",
  "tagline": "Fresh Pasta Made Daily",
  "description": "Family-owned Italian restaurant serving handmade pasta and locally sourced ingredients since 1998.",
  "year_founded": 1998,

  "brand_identity": {
    "primary_color": "#D4341F",
    "secondary_color": "#FFF8E7",
    "accent_color": "#2E7D32",
    "text_color_dark": "#1A1A1A",
    "text_color_light": "#FFFFFF",
    "background_color": "#FFF8E7",

    "font_heading": "Playfair Display",
    "font_heading_fallback": "Georgia",
    "font_body": "Open Sans",
    "font_body_fallback": "Arial",
    "font_accent": "Dancing Script",

    "logo_path": "",
    "logo_light_path": "",
    "logo_icon_path": "",
    "favicon_path": "",

    "photography_style": "warm, rustic, close-up food photography with natural lighting and shallow depth of field",
    "illustration_style": "hand-drawn, vintage Italian, warm earth tones",
    "icon_style": "line icons, rounded, warm colors"
  },

  "voice": {
    "tone": "warm",
    "formality": "casual",
    "personality": ["friendly", "passionate", "family-oriented", "authentic"],
    "vocabulary_include": ["handmade", "fresh", "family", "locally sourced", "tradition"],
    "vocabulary_avoid": ["cheap", "fast food", "processed", "discount"],
    "cta_style": "inviting",
    "sample_headlines": [
      "Fresh Pasta Made Daily",
      "Taste the Family Tradition",
      "Where Every Meal Tells a Story"
    ],
    "sample_ctas": [
      "Reserve Your Table",
      "Order Now",
      "View Our Menu",
      "Visit Us Today"
    ]
  },

  "audience": {
    "primary_demo": "Families and couples aged 30-55",
    "secondary_demo": "Food enthusiasts and tourists",
    "income_level": "middle to upper-middle",
    "interests": ["dining out", "Italian cuisine", "local food scene", "date nights"],
    "pain_points": ["finding authentic restaurants", "chain restaurant fatigue", "dietary accommodations"],
    "geographic_radius_miles": 15,
    "location": {
      "address": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "zip": "62701",
      "country": "US"
    }
  },

  "competitors": [
    {
      "name": "Olive Garden",
      "type": "chain",
      "differentiator": "We're locally owned with handmade pasta, they use factory-made"
    },
    {
      "name": "Bella Notte",
      "type": "local",
      "differentiator": "We've been here 25 years, stronger community roots"
    }
  ],

  "usps": [
    "Handmade pasta daily — never frozen, never factory",
    "Locally sourced ingredients from Springfield farmers",
    "Family-owned for 25+ years",
    "Private dining for events up to 40 guests"
  ],

  "platforms": {
    "instagram": {"handle": "@mariosbistro", "active": true, "posting_freq": "4x/week"},
    "facebook": {"handle": "MariosBistroSpringfield", "active": true, "posting_freq": "3x/week"},
    "google_business": {"active": true, "posting_freq": "2x/week"},
    "tiktok": {"handle": "@mariosbistro", "active": false},
    "twitter": {"handle": "", "active": false},
    "youtube": {"handle": "", "active": false},
    "linkedin": {"handle": "", "active": false},
    "website": "https://mariosbistro.com",
    "online_ordering": "https://order.mariosbistro.com"
  },

  "asset_preferences": {
    "image_style_default": "photorealistic",
    "video_duration_default_seconds": 15,
    "video_aspect_ratio_default": "9:16",
    "deck_theme": "warm_professional",
    "preferred_cta_color": "#D4341F",
    "watermark_logo": true,
    "watermark_position": "bottom_right"
  },

  "seasonal_themes": [
    {"month_range": [11, 12], "theme": "Holiday Specials", "colors_override": ["#D4341F", "#2E7D32", "#FFD700"]},
    {"month_range": [6, 8], "theme": "Summer Patio Dining", "colors_override": null},
    {"month_range": [2, 2], "theme": "Valentine's Date Night", "colors_override": ["#E91E63", "#FFF8E7"]}
  ],

  "generated_assets_log": [],

  "metadata": {
    "created_at": "",
    "updated_at": "",
    "onboarded_by": "",
    "notes": ""
  }
}
```

## Multi-Client Storage Architecture

```
brand_profiles/
├── index.json                      # Client registry: {client_id: {name, industry, path, active}}
├── marios-bistro/
│   ├── profile.json                # Full brand profile
│   ├── assets/
│   │   ├── logo.png                # Primary logo
│   │   ├── logo-light.png          # Light/white version
│   │   ├── logo-icon.png           # Icon-only version
│   │   └── brand-fonts/            # Custom font files (if any)
│   ├── templates/
│   │   ├── social_post.json        # Saved Pillow template configs
│   │   ├── video_intro.json        # Saved MoviePy intro template
│   │   └── pitch_deck.pptx         # Branded PPTX template
│   └── history/
│       └── generated_assets.jsonl  # Log of all generated assets
├── joes-pizza/
│   ├── profile.json
│   ├── assets/
│   └── ...
└── sunny-yoga/
    ├── profile.json
    ├── assets/
    └── ...
```

## Implementation: Brand Profile Manager

```python
import json
import os
from datetime import datetime
from pathlib import Path

# ─── CONFIGURATION ─────────────────────────────────────────
BRAND_PROFILES_DIR = os.environ.get("BRAND_PROFILES_DIR", "./brand_profiles")

# ─── BRAND PROFILE MANAGER ─────────────────────────────────

class BrandProfileManager:
    """Manages multi-client brand profiles for autonomous agent pipelines."""

    def __init__(self, profiles_dir=None):
        self.profiles_dir = Path(profiles_dir or BRAND_PROFILES_DIR)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.profiles_dir / "index.json"
        self._ensure_index()

    def _ensure_index(self):
        if not self.index_path.exists():
            self._write_json(self.index_path, {"clients": {}})

    def _read_json(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ─── CLIENT REGISTRY ────────────────────────────────────

    def list_clients(self):
        """List all registered clients."""
        index = self._read_json(self.index_path)
        return index.get("clients", {})

    def get_client_ids(self):
        """Get list of all client IDs."""
        return list(self.list_clients().keys())

    # ─── PROFILE CRUD ───────────────────────────────────────

    def create_profile(self, client_id, profile_data):
        """
        Create a new client brand profile.

        client_id: lowercase-hyphenated identifier (e.g. 'marios-bistro')
        profile_data: dict matching the Brand Profile JSON Schema
        """
        client_dir = self.profiles_dir / client_id
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "assets").mkdir(exist_ok=True)
        (client_dir / "templates").mkdir(exist_ok=True)
        (client_dir / "history").mkdir(exist_ok=True)

        # Set metadata
        now = datetime.now().isoformat()
        profile_data["client_id"] = client_id
        profile_data["schema_version"] = "1.0"
        profile_data.setdefault("metadata", {})
        profile_data["metadata"]["created_at"] = now
        profile_data["metadata"]["updated_at"] = now
        profile_data.setdefault("generated_assets_log", [])

        # Validate required fields
        self._validate_profile(profile_data)

        # Save profile
        profile_path = client_dir / "profile.json"
        self._write_json(profile_path, profile_data)

        # Update index
        index = self._read_json(self.index_path)
        index["clients"][client_id] = {
            "name": profile_data.get("business_name", client_id),
            "industry": profile_data.get("industry", "unknown"),
            "path": str(client_dir),
            "active": True,
            "created_at": now
        }
        self._write_json(self.index_path, index)

        return profile_data

    def get_profile(self, client_id):
        """Load a client's full brand profile."""
        profile_path = self.profiles_dir / client_id / "profile.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"No brand profile found for client '{client_id}'. Run onboarding first.")
        return self._read_json(profile_path)

    def update_profile(self, client_id, updates):
        """
        Partially update a client's brand profile.
        
        updates: dict of fields to update (supports nested dot notation keys)
        Example: {"brand_identity.primary_color": "#FF0000", "tagline": "New tagline"}
        """
        profile = self.get_profile(client_id)

        for key, value in updates.items():
            parts = key.split(".")
            target = profile
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value

        profile["metadata"]["updated_at"] = datetime.now().isoformat()
        profile_path = self.profiles_dir / client_id / "profile.json"
        self._write_json(profile_path, profile)
        return profile

    def delete_profile(self, client_id):
        """Remove a client profile (marks inactive, does not delete files)."""
        index = self._read_json(self.index_path)
        if client_id in index["clients"]:
            index["clients"][client_id]["active"] = False
            self._write_json(self.index_path, index)

    # ─── BRAND EXTRACTION HELPERS ───────────────────────────

    def get_colors(self, client_id):
        """Get brand colors for a client."""
        p = self.get_profile(client_id)
        bi = p.get("brand_identity", {})
        return {
            "primary": bi.get("primary_color", "#2563EB"),
            "secondary": bi.get("secondary_color", "#1E40AF"),
            "accent": bi.get("accent_color", "#F59E0B"),
            "text_dark": bi.get("text_color_dark", "#1A1A1A"),
            "text_light": bi.get("text_color_light", "#FFFFFF"),
            "background": bi.get("background_color", "#FFFFFF"),
        }

    def get_fonts(self, client_id):
        """Get font preferences for a client."""
        p = self.get_profile(client_id)
        bi = p.get("brand_identity", {})
        return {
            "heading": bi.get("font_heading", "Calibri"),
            "heading_fallback": bi.get("font_heading_fallback", "Arial"),
            "body": bi.get("font_body", "Calibri"),
            "body_fallback": bi.get("font_body_fallback", "Arial"),
            "accent": bi.get("font_accent", ""),
        }

    def get_voice(self, client_id):
        """Get brand voice and tone settings."""
        p = self.get_profile(client_id)
        return p.get("voice", {})

    def get_logo_path(self, client_id, variant="primary"):
        """Get the path to the client's logo file."""
        p = self.get_profile(client_id)
        bi = p.get("brand_identity", {})
        key_map = {
            "primary": "logo_path",
            "light": "logo_light_path",
            "icon": "logo_icon_path",
        }
        logo = bi.get(key_map.get(variant, "logo_path"), "")
        if logo and os.path.exists(logo):
            return logo
        return None

    def get_cta(self, client_id, context="default"):
        """Get a contextually appropriate CTA for the client."""
        voice = self.get_voice(client_id)
        ctas = voice.get("sample_ctas", ["Learn More"])
        # Simple rotation; in production, use context-aware selection
        if context == "social":
            return ctas[1] if len(ctas) > 1 else ctas[0]
        elif context == "ad":
            return ctas[0]
        return ctas[0]

    def get_seasonal_override(self, client_id, month=None):
        """Check if there's a seasonal color/theme override for this month."""
        import datetime as dt
        month = month or dt.datetime.now().month
        p = self.get_profile(client_id)
        for theme in p.get("seasonal_themes", []):
            r = theme.get("month_range", [])
            if len(r) == 2 and r[0] <= month <= r[1]:
                return theme
        return None

    def get_platforms(self, client_id, active_only=True):
        """Get the client's active social media platforms."""
        p = self.get_profile(client_id)
        platforms = p.get("platforms", {})
        if active_only:
            return {k: v for k, v in platforms.items()
                    if isinstance(v, dict) and v.get("active", False)}
        return platforms

    def get_asset_prefs(self, client_id):
        """Get default asset generation preferences."""
        p = self.get_profile(client_id)
        return p.get("asset_preferences", {})

    # ─── ASSET LOGGING ──────────────────────────────────────

    def log_generated_asset(self, client_id, asset_type, file_path, metadata=None):
        """Log a generated asset to the client's history."""
        history_path = self.profiles_dir / client_id / "history" / "generated_assets.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": asset_type,
            "file_path": str(file_path),
            "metadata": metadata or {}
        }
        with open(history_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_asset_history(self, client_id, asset_type=None, limit=50):
        """Retrieve recent generated assets for a client."""
        history_path = self.profiles_dir / client_id / "history" / "generated_assets.jsonl"
        if not history_path.exists():
            return []
        entries = []
        with open(history_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if asset_type is None or entry.get("type") == asset_type:
                        entries.append(entry)
        return entries[-limit:]

    # ─── VALIDATION ─────────────────────────────────────────

    def _validate_profile(self, profile):
        """Validate a brand profile has minimum required fields."""
        required = ["business_name", "industry", "brand_identity", "voice"]
        missing = [f for f in required if not profile.get(f)]
        if missing:
            raise ValueError(f"Brand profile missing required fields: {missing}")

        bi = profile.get("brand_identity", {})
        if not bi.get("primary_color"):
            raise ValueError("brand_identity.primary_color is required")

        voice = profile.get("voice", {})
        if not voice.get("tone"):
            raise ValueError("voice.tone is required")

    # ─── ONBOARDING FLOW ────────────────────────────────────

    def onboard_from_minimal(self, client_id, business_name, industry,
                               primary_color, tone="friendly", tagline="",
                               description="", logo_path=""):
        """
        Quick onboard a client with minimal required info.
        Auto-fills sensible defaults based on industry.

        This is the entry point for autonomous onboarding — the agent can
        call this with just a few fields and get a complete profile.
        """
        INDUSTRY_DEFAULTS = {
            "restaurant": {
                "photography_style": "warm, appetizing food photography, close-up with natural lighting, rustic table settings",
                "illustration_style": "hand-drawn menu style, warm earth tones",
                "audience_primary": "Families and food enthusiasts aged 25-55",
                "audience_interests": ["dining out", "local food", "date nights", "family meals"],
                "platforms_default": ["instagram", "facebook", "google_business"],
                "cta_style": "inviting",
                "video_duration": 15,
                "sample_ctas": ["Reserve Your Table", "Order Now", "View Our Menu", "Visit Us Today"],
            },
            "retail": {
                "photography_style": "clean product photography, white background, lifestyle shots",
                "illustration_style": "modern, clean, brand-colored illustrations",
                "audience_primary": "Shoppers aged 20-45",
                "audience_interests": ["shopping", "fashion", "deals", "local stores"],
                "platforms_default": ["instagram", "facebook", "tiktok"],
                "cta_style": "action-oriented",
                "video_duration": 15,
                "sample_ctas": ["Shop Now", "Get Yours", "Limited Time Offer", "Visit Our Store"],
            },
            "fitness": {
                "photography_style": "energetic, dynamic action shots, bright lighting, motivational",
                "illustration_style": "bold, high-contrast, athletic style",
                "audience_primary": "Health-conscious adults aged 20-45",
                "audience_interests": ["fitness", "health", "wellness", "personal training"],
                "platforms_default": ["instagram", "tiktok", "youtube"],
                "cta_style": "motivational",
                "video_duration": 30,
                "sample_ctas": ["Start Your Journey", "Join Today", "Book a Class", "Free Trial"],
            },
            "salon": {
                "photography_style": "glamorous, well-lit beauty shots, before/after, warm tones",
                "illustration_style": "elegant, feminine, soft pastels",
                "audience_primary": "Women aged 20-50",
                "audience_interests": ["beauty", "self-care", "hair styling", "skincare"],
                "platforms_default": ["instagram", "facebook", "tiktok"],
                "cta_style": "inviting",
                "video_duration": 15,
                "sample_ctas": ["Book Your Appointment", "Transform Your Look", "Treat Yourself", "View Styles"],
            },
            "professional_services": {
                "photography_style": "corporate, clean headshots, modern office environments",
                "illustration_style": "minimal, professional infographics, flat design",
                "audience_primary": "Business professionals and decision-makers aged 30-60",
                "audience_interests": ["business growth", "efficiency", "professional development"],
                "platforms_default": ["linkedin", "facebook", "google_business"],
                "cta_style": "professional",
                "video_duration": 30,
                "sample_ctas": ["Schedule a Consultation", "Learn More", "Get Started", "Contact Us"],
            },
            "default": {
                "photography_style": "professional, clean, well-lit",
                "illustration_style": "modern, clean design",
                "audience_primary": "General consumers aged 25-55",
                "audience_interests": ["local businesses", "quality products"],
                "platforms_default": ["instagram", "facebook"],
                "cta_style": "friendly",
                "video_duration": 15,
                "sample_ctas": ["Learn More", "Visit Us", "Get Started", "Contact Us"],
            },
        }

        defaults = INDUSTRY_DEFAULTS.get(industry, INDUSTRY_DEFAULTS["default"])

        # Build platform config from industry defaults
        platforms_config = {}
        for platform in defaults["platforms_default"]:
            platforms_config[platform] = {"handle": "", "active": True, "posting_freq": "3x/week"}

        profile = {
            "business_name": business_name,
            "industry": industry,
            "tagline": tagline,
            "description": description or f"{business_name} — a local {industry} business.",

            "brand_identity": {
                "primary_color": primary_color,
                "secondary_color": self._generate_secondary_color(primary_color),
                "accent_color": "#F59E0B",
                "text_color_dark": "#1A1A1A",
                "text_color_light": "#FFFFFF",
                "background_color": "#FFFFFF",
                "font_heading": "Calibri",
                "font_heading_fallback": "Arial",
                "font_body": "Calibri",
                "font_body_fallback": "Arial",
                "font_accent": "",
                "logo_path": logo_path,
                "logo_light_path": "",
                "logo_icon_path": "",
                "favicon_path": "",
                "photography_style": defaults["photography_style"],
                "illustration_style": defaults["illustration_style"],
                "icon_style": "line icons, rounded",
            },

            "voice": {
                "tone": tone,
                "formality": "casual" if tone in ["friendly", "playful", "warm"] else "formal",
                "personality": [tone, "authentic", "local"],
                "vocabulary_include": [],
                "vocabulary_avoid": [],
                "cta_style": defaults["cta_style"],
                "sample_headlines": [tagline] if tagline else [f"Welcome to {business_name}"],
                "sample_ctas": defaults["sample_ctas"],
            },

            "audience": {
                "primary_demo": defaults["audience_primary"],
                "interests": defaults["audience_interests"],
                "geographic_radius_miles": 15,
                "location": {}
            },

            "competitors": [],
            "usps": [],

            "platforms": platforms_config,

            "asset_preferences": {
                "image_style_default": "photorealistic",
                "video_duration_default_seconds": defaults["video_duration"],
                "video_aspect_ratio_default": "9:16",
                "deck_theme": "professional",
                "preferred_cta_color": primary_color,
                "watermark_logo": bool(logo_path),
                "watermark_position": "bottom_right"
            },

            "seasonal_themes": [],
        }

        return self.create_profile(client_id, profile)

    def _generate_secondary_color(self, hex_color):
        """Generate a darker secondary color from the primary."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        # Darken by 30%
        r2, g2, b2 = max(0, int(r * 0.7)), max(0, int(g * 0.7)), max(0, int(b * 0.7))
        return f"#{r2:02X}{g2:02X}{b2:02X}"
```

## How Other Skills Consume Brand Profiles

Every generation function in the image, video, and pitch deck skills should accept
a `client_id` parameter and load the brand profile at the start.

### Pattern: Brand-Aware Function Wrapper

```python
def brand_aware(func):
    """Decorator that injects brand profile into any generation function."""
    import functools
    @functools.wraps(func)
    def wrapper(*args, client_id=None, **kwargs):
        if client_id:
            mgr = BrandProfileManager()
            brand = mgr.get_profile(client_id)
            kwargs["_brand"] = brand

            # Auto-inject common brand values if not explicitly provided
            colors = mgr.get_colors(client_id)
            if "brand_color" not in kwargs:
                kwargs["brand_color"] = colors["primary"]
            if "text_color" not in kwargs:
                kwargs["text_color"] = colors["text_light"]

            voice = mgr.get_voice(client_id)
            if "cta_text" not in kwargs and voice.get("sample_ctas"):
                kwargs["cta_text"] = voice["sample_ctas"][0]

            logo = mgr.get_logo_path(client_id)
            if logo and "logo_path" not in kwargs:
                kwargs["logo_path"] = logo
        
        result = func(*args, **kwargs)

        # Log the generated asset
        if client_id and result:
            mgr.log_generated_asset(
                client_id,
                asset_type=func.__name__,
                file_path=result,
                metadata={"kwargs": {k: str(v) for k, v in kwargs.items() if k != "_brand"}}
            )
        return result
    return wrapper
```

### Integration Example: Image Generation

```python
# In image-generation-agent SKILL.md, wrap the social graphic function:

@brand_aware
def create_social_media_graphic(background_image_path, headline, subtext,
                                 cta_text=None, brand_color=None,
                                 platform="instagram_post", **kwargs):
    # brand_color and cta_text are auto-injected from profile if client_id is provided
    # The function body stays the same — it just receives brand-correct defaults
    ...
```

### Integration Example: Video Ad Generation

```python
# In video-ad-generation SKILL.md:

def generate_ad_script(client_id, promotion_details):
    """Generate a video ad script using the client's brand voice."""
    mgr = BrandProfileManager()
    brand = mgr.get_profile(client_id)
    voice = brand["voice"]
    
    script_prompt = f"""
    Create a {brand['asset_preferences']['video_duration_default_seconds']}-second video ad script
    for {brand['business_name']}.
    
    Business: {brand['description']}
    Tagline: {brand['tagline']}
    Tone: {voice['tone']}, {voice['formality']}
    Personality: {', '.join(voice['personality'])}
    Words to include: {', '.join(voice['vocabulary_include'])}
    Words to avoid: {', '.join(voice['vocabulary_avoid'])}
    CTA style: {voice['cta_style']}
    Sample CTAs: {', '.join(voice['sample_ctas'])}
    
    Promotion: {promotion_details}
    
    Photography direction: {brand['brand_identity']['photography_style']}
    Brand colors: primary={brand['brand_identity']['primary_color']}, 
                  secondary={brand['brand_identity']['secondary_color']}
    
    Return a JSON array of scenes with: visual_prompt, text_overlay, voiceover_text, duration
    """
    # Pass to LLM for script generation
    return script_prompt
```

### Integration Example: Pitch Deck Generation

```python
# In pitch-deck-generation SKILL.md:

def build_branded_deck(client_id, deck_content):
    """Build a pitch deck using the client's brand colors and fonts."""
    mgr = BrandProfileManager()
    brand = mgr.get_profile(client_id)
    colors = mgr.get_colors(client_id)
    fonts = mgr.get_fonts(client_id)

    deck_data = {
        **deck_content,
        "design": {
            "primary_color": colors["primary"],
            "secondary_color": colors["secondary"],
            "accent_color": colors["accent"],
            "font_heading": fonts["heading"],
            "font_body": fonts["body"],
            "theme": brand.get("asset_preferences", {}).get("deck_theme", "professional")
        }
    }
    # Pass to create_pitch_deck() function
    return create_pitch_deck(deck_data, output_path)
```

## Onboarding Workflow for Agents

When an agent receives a task for a NEW client (no existing profile):

```
1. DETECT: Is there a brand profile for this client?
   → mgr.get_client_ids() to check

2. IF NO PROFILE EXISTS:
   a. Extract brand info from context:
      - Business name, industry from the request
      - Colors from their website (fetch and parse CSS)
      - Logo from their website or social media
      - Tone from their existing social media posts
   
   b. Quick onboard with minimal info:
      mgr.onboard_from_minimal(
          client_id="marios-bistro",
          business_name="Mario's Bistro",
          industry="restaurant",
          primary_color="#D4341F",
          tone="warm",
          tagline="Fresh Pasta Made Daily"
      )
   
   c. Optionally enrich profile:
      mgr.update_profile("marios-bistro", {
          "voice.vocabulary_include": ["handmade", "fresh", "family"],
          "audience.location.city": "Springfield",
          "competitors": [{"name": "Olive Garden", "type": "chain"}]
      })

3. IF PROFILE EXISTS:
   → Load it and proceed with asset generation

4. GENERATE ASSETS:
   → Pass client_id to every generation function
   → Brand colors, fonts, voice, logo are auto-injected
```

## Auto-Learn Brand from Website

```python
import requests
import re

def learn_brand_from_website(url):
    """
    Attempt to extract brand colors, logo, and description from a website.
    Returns a partial profile dict that can be passed to onboard_from_minimal.
    """
    try:
        response = requests.get(url, timeout=10)
        html = response.text

        # Extract colors from CSS
        colors = re.findall(r'#[0-9A-Fa-f]{6}', html)
        # Filter out common non-brand colors (white, black, greys)
        brand_colors = [c for c in colors if c.lower() not in
                        ['#ffffff', '#000000', '#333333', '#666666', '#999999',
                         '#cccccc', '#f5f5f5', '#eeeeee', '#dddddd']]
        primary_color = brand_colors[0] if brand_colors else "#2563EB"

        # Extract title / description
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract logo
        logo_match = re.search(r'<img[^>]*(?:class|id)[^>]*logo[^>]*src=["\'](.*?)["\']', html, re.IGNORECASE)
        if not logo_match:
            logo_match = re.search(r'<link[^>]*rel=["\']icon["\'][^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
        logo_url = logo_match.group(1) if logo_match else ""

        return {
            "primary_color": primary_color,
            "description": description,
            "title": title,
            "logo_url": logo_url,
        }
    except Exception:
        return {"primary_color": "#2563EB", "description": "", "title": "", "logo_url": ""}
```

## Key Principles

1. **Brand first, always.** No asset should be generated without loading the client profile. If no profile exists, create one — even a minimal one — before proceeding.

2. **Fail gracefully.** If a profile field is missing, use sensible defaults from the industry template. Never block generation because a secondary color isn't set.

3. **One source of truth.** The profile.json is the canonical brand definition. Don't hardcode colors or fonts in generation functions.

4. **Log everything.** Every generated asset is logged with timestamp and metadata. This enables performance tracking and prevents regenerating the same content.

5. **Seasonal awareness.** Check for seasonal overrides before every generation. A Valentine's Day post should use pink, not the usual brand blue.

6. **Progressive enrichment.** Start with minimal onboarding (5 fields), then enrich over time as the agent learns more about the client from their website, social media, and feedback.

7. **Client isolation.** Each client has their own directory with assets, templates, and history. No cross-contamination between clients.

8. **Agent autonomy.** The onboard_from_minimal function with industry defaults means an agent can onboard a new client in a single function call with just a name, industry, and color — no human input needed.
