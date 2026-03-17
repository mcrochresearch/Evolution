---
name: website-builder-agent
description: >
  Autonomous website builder skill for AI agents. Use when an agent needs to generate
  complete small business websites from a brand profile — including multi-page static sites
  with industry-specific templates (restaurant, retail, salon, fitness), Jinja2+Tailwind CSS
  rendering, full SEO (meta tags, sitemap.xml, robots.txt, JSON-LD LocalBusiness schema),
  and deployment to Cloudflare Pages, Netlify, or GitHub Pages via API. Integrates with
  client-brand-profile skill for multi-client, brand-aware site generation. Designed for
  autonomous operation with no human intervention required.
metadata:
  author: localcomm
  version: '1.0'
  updated: '2026-03-15'
---

# Website Builder for Autonomous AI Agents

## When to Use This Skill

Use this skill when an AI agent needs to:

- Generate a complete small business website from a brand profile
- Build industry-specific sites (restaurant with menu/hours, salon with services/booking, etc.)
- Create responsive, mobile-first static sites with Tailwind CSS
- Produce SEO-optimized pages with meta tags, JSON-LD schema, and sitemap
- Deploy static sites to Cloudflare Pages, Netlify, or GitHub Pages
- Manage multi-client websites through the brand profile system
- Update or regenerate specific pages for an existing client site

## Free Tool Stack (As of March 2026)

### Tier 1: Static Site Generation (Free, Open Source)

#### 1. Jinja2 + Tailwind CSS (Primary — Used in This Skill)
- **What**: Python template engine + utility-first CSS framework
- **License**: BSD-3 (Jinja2), MIT (Tailwind)
- **Cost**: Completely free
- **Best For**: Programmatic, agent-driven site generation with full template control
- **Install**: `pip install Jinja2` + Tailwind CDN or CLI
- **Why Primary**: Agents can generate and modify templates programmatically without a build toolchain

#### 2. Astro
- **What**: Modern static site generator with island architecture
- **License**: MIT
- **Stars**: 50K+ on GitHub
- **Strengths**: Perfect Lighthouse scores, zero JS by default, component islands
- **Best For**: Complex sites where you need interactive islands (booking widgets, maps)
- **URL**: https://astro.build

#### 3. Hugo
- **What**: Go-based static site generator, fastest build times
- **License**: Apache 2.0
- **Strengths**: Sub-second builds, thousands of themes, built-in sitemap/RSS, multilingual
- **Best For**: Blog-heavy sites, content-driven businesses
- **URL**: https://gohugo.io

#### 4. Eleventy (11ty)
- **What**: JavaScript-based static site generator
- **License**: MIT
- **Strengths**: Lightweight, flexible, SEO-friendly, multiple template languages
- **Best For**: Simple sites, portfolios, landing pages
- **URL**: https://www.11ty.dev

### Tier 2: Visual Builder Frameworks (Free, Open Source)

#### 5. GrapesJS
- **What**: Open-source drag-and-drop web builder framework
- **License**: BSD-3
- **Strengths**: Outputs clean HTML/CSS/JSON, fully customizable, white-label capable
- **API**: Embeddable editor with programmatic block/component management
- **URL**: https://grapesjs.com
- **Best For**: When clients want to visually edit their site after generation

#### 6. TeleportHQ
- **What**: Visual builder with AI UI generation
- **Strengths**: Exports React/Vue/HTML/CSS, AI layout generation
- **Free Tier**: Unlimited projects
- **URL**: https://teleporthq.io

### Tier 3: Headless CMS (Free Tiers)

#### 7. Strapi
- **What**: Open-source headless CMS, self-hosted
- **License**: MIT (Community Edition)
- **Free Tier**: Unlimited — self-hosted community plan
- **API**: REST + GraphQL
- **Best For**: Sites needing content management (menus, services, blog posts)
- **URL**: https://strapi.io

#### 8. Sanity
- **What**: Real-time headless CMS
- **Free Tier**: 20 users, unlimited admin, 500K API CDN requests/month
- **API**: GROQ + GraphQL + REST
- **Best For**: Structured content (menus, product catalogs, class schedules)
- **URL**: https://www.sanity.io

#### 9. Contentful
- **What**: Enterprise headless CMS with free community tier
- **Free Tier**: 5 users, 100K API calls/month, 25K records
- **API**: REST + GraphQL
- **URL**: https://www.contentful.com

### Tier 4: Free Hosting & Deployment

#### 10. Cloudflare Pages
- **What**: JAMstack hosting with global CDN
- **Free Tier**: Unlimited bandwidth, 500 builds/month, custom domains, automatic SSL
- **API**: Full REST API for deployments — `POST /pages/projects/{name}/deployments`
- **URL**: https://pages.cloudflare.com
- **Best For**: Production small business sites (best free hosting option)

#### 11. Netlify
- **What**: Static site hosting with CI/CD
- **Free Tier**: 100GB bandwidth, 300 build minutes/month, custom domains, automatic SSL
- **API**: REST API for deploy — upload zip via `POST /sites/{site_id}/deploys`
- **URL**: https://www.netlify.com

#### 12. Vercel
- **What**: Frontend hosting optimized for frameworks
- **Free Tier**: 100GB bandwidth, custom domains, serverless functions
- **URL**: https://vercel.com

#### 13. GitHub Pages
- **What**: Static hosting from GitHub repos
- **Free Tier**: Unlimited for public repos, 1GB storage, 100GB bandwidth/month
- **API**: Push to `gh-pages` branch or use GitHub Actions
- **URL**: https://pages.github.com
- **Best For**: Simple static sites, easiest deployment via git push

### Tier 5: Website Builder APIs

#### 14. 10Web API
- **What**: AI-generated WordPress websites from text prompts
- **Free Tier**: 1 site free with hosting
- **API**: REST API for site creation and management
- **URL**: https://10web.io

#### 15. Brizy Cloud
- **What**: Embeddable visual builder with REST API
- **Strengths**: White-label, embeddable in SaaS products
- **API**: Full REST API for programmatic site management
- **URL**: https://www.brizy.io

#### 16. Pexels API (Free Stock Images)
- **What**: Free stock photo API for site imagery
- **Free Tier**: 200 requests/hour, no attribution required
- **API**: REST — search and download photos/videos
- **URL**: https://www.pexels.com/api/
- **Best For**: Hero images, background photos, placeholder imagery

#### 17. Google Fonts API
- **What**: Free web fonts for branding
- **Free Tier**: Unlimited, all fonts free
- **API**: CSS link or self-host via `google-webfonts-helper`
- **URL**: https://fonts.google.com
- **Best For**: Loading brand fonts specified in client profiles

## Autonomous Website Generation Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     AGENT ORCHESTRATOR                          │
│              (LLM: Gemini/GPT/Ollama/Local)                    │
└──────────────────────┬─────────────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     BRAND PROFILE LOADER     │
        │  BrandProfileManager.        │
        │  get_profile(client_id)      │
        │  → colors, fonts, voice,     │
        │    logo, industry, content   │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    TEMPLATE SELECTOR         │
        │  Industry → template map:    │
        │  restaurant: menu, hours,    │
        │    reservations, reviews     │
        │  retail: products, shop,     │
        │    about, contact            │
        │  salon: services, booking,   │
        │    gallery, about            │
        │  fitness: classes, schedule, │
        │    trainers, pricing         │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     CONTENT GENERATOR        │
        │  LLM generates per-page:     │
        │  - Hero headlines & CTAs     │
        │  - About copy from profile   │
        │  - Service/menu descriptions │
        │  - SEO meta tags & titles    │
        │  - Image alt text            │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    JINJA2 + TAILWIND         │
        │    SITE RENDERER             │
        │                              │
        │  For each page:              │
        │  - Load industry template    │
        │  - Inject brand vars         │
        │  - Render HTML with Jinja2   │
        │  - Apply Tailwind classes    │
        │  - Write to output dir       │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │      SEO OPTIMIZER           │
        │                              │
        │  - sitemap.xml               │
        │  - robots.txt                │
        │  - manifest.json             │
        │  - JSON-LD LocalBusiness     │
        │  - Open Graph meta tags      │
        │  - Canonical URLs            │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     DEPLOYMENT PIPELINE      │
        │                              │
        │  Primary: Cloudflare Pages   │
        │  Backup: Netlify             │
        │  Fallback: GitHub Pages      │
        │                              │
        │  - Upload static files       │
        │  - Configure custom domain   │
        │  - Verify SSL/HTTPS          │
        └──────────────────────────────┘
```

## Implementation Guide

### Step 1: Multi-Client Website Manager

```python
import json
import os
import shutil
from pathlib import Path
from datetime import datetime

# ─── CONFIGURATION ─────────────────────────────────────────
BRAND_PROFILES_DIR = os.environ.get("BRAND_PROFILES_DIR", "./brand_profiles")
SITES_OUTPUT_DIR = os.environ.get("SITES_OUTPUT_DIR", "./generated_sites")
TEMPLATES_DIR = os.environ.get("TEMPLATES_DIR", "./website_templates")

# Import BrandProfileManager from client-brand-profile skill
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brand_profile_manager import BrandProfileManager


class WebsiteManager:
    """Manages multi-client website generation using brand profiles."""

    def __init__(self, profiles_dir=None, output_dir=None, templates_dir=None):
        self.brand_mgr = BrandProfileManager(profiles_dir or BRAND_PROFILES_DIR)
        self.output_dir = Path(output_dir or SITES_OUTPUT_DIR)
        self.templates_dir = Path(templates_dir or TEMPLATES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_site_dir(self, client_id):
        """Get the output directory for a client's website."""
        site_dir = self.output_dir / client_id
        site_dir.mkdir(parents=True, exist_ok=True)
        return site_dir

    def generate_site(self, client_id, pages=None, base_url=None):
        """
        Generate a complete website for a client from their brand profile.

        client_id: registered client ID from brand profile system
        pages: optional list of page names to generate (default: all for industry)
        base_url: the site's base URL for SEO (e.g., "https://mariosbistro.com")
        """
        try:
            profile = self.brand_mgr.get_profile(client_id)
        except FileNotFoundError:
            raise ValueError(
                f"No brand profile for '{client_id}'. "
                "Onboard the client first via BrandProfileManager.onboard_from_minimal()."
            )

        industry = profile.get("industry", "default")
        site_dir = self.get_site_dir(client_id)

        # Determine pages for this industry
        if pages is None:
            pages = get_industry_pages(industry)

        # Resolve base_url from profile or argument
        if base_url is None:
            platforms = profile.get("platforms", {})
            base_url = platforms.get("website", f"https://{client_id}.example.com")

        # Build template context from brand profile
        context = build_template_context(profile, base_url)

        # Render each page
        rendered_pages = []
        for page_name in pages:
            try:
                html = render_page(industry, page_name, context)
                page_filename = "index.html" if page_name == "home" else f"{page_name}.html"
                page_path = site_dir / page_filename
                page_path.write_text(html, encoding="utf-8")
                rendered_pages.append(page_name)
            except Exception as e:
                print(f"Warning: Failed to render '{page_name}' for {client_id}: {e}")
                continue

        # Generate SEO files
        generate_sitemap(site_dir, rendered_pages, base_url)
        generate_robots_txt(site_dir, base_url)
        generate_manifest(site_dir, profile)

        # Generate JSON-LD LocalBusiness schema
        schema_json = generate_local_business_schema(profile, base_url)
        (site_dir / "schema.json").write_text(
            json.dumps(schema_json, indent=2), encoding="utf-8"
        )

        # Copy static assets (logo, favicon)
        copy_brand_assets(self.brand_mgr, client_id, site_dir)

        # Log the generation
        self.brand_mgr.log_generated_asset(
            client_id,
            asset_type="website",
            file_path=str(site_dir),
            metadata={
                "pages": rendered_pages,
                "base_url": base_url,
                "industry": industry,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return {
            "site_dir": str(site_dir),
            "pages": rendered_pages,
            "base_url": base_url,
            "industry": industry,
        }

    def regenerate_page(self, client_id, page_name, base_url=None):
        """Regenerate a single page for an existing client site."""
        profile = self.brand_mgr.get_profile(client_id)
        industry = profile.get("industry", "default")
        site_dir = self.get_site_dir(client_id)

        if base_url is None:
            platforms = profile.get("platforms", {})
            base_url = platforms.get("website", f"https://{client_id}.example.com")

        context = build_template_context(profile, base_url)
        html = render_page(industry, page_name, context)
        page_filename = "index.html" if page_name == "home" else f"{page_name}.html"
        (site_dir / page_filename).write_text(html, encoding="utf-8")

        # Regenerate sitemap with updated timestamp
        existing_pages = [
            f.stem if f.stem != "index" else "home"
            for f in site_dir.glob("*.html")
        ]
        generate_sitemap(site_dir, existing_pages, base_url)

        return str(site_dir / page_filename)

    def list_client_sites(self):
        """List all generated client sites."""
        sites = {}
        if self.output_dir.exists():
            for d in self.output_dir.iterdir():
                if d.is_dir() and (d / "index.html").exists():
                    pages = [
                        f.stem if f.stem != "index" else "home"
                        for f in d.glob("*.html")
                    ]
                    sites[d.name] = {"path": str(d), "pages": pages}
        return sites
```

### Step 2: Industry-Specific Page Definitions

```python
# ─── INDUSTRY PAGE MAPS ───────────────────────────────────

INDUSTRY_PAGES = {
    "restaurant": ["home", "about", "menu", "contact", "reviews"],
    "retail": ["home", "about", "products", "contact", "reviews"],
    "salon": ["home", "about", "services", "booking", "contact"],
    "fitness": ["home", "about", "classes", "schedule", "contact"],
    "professional_services": ["home", "about", "services", "contact", "reviews"],
    "default": ["home", "about", "services", "contact"],
}

# Restaurant-specific content sections
RESTAURANT_SECTIONS = {
    "home": ["hero", "featured_dishes", "hours", "location_map", "cta_reservation"],
    "menu": ["menu_categories", "specials", "dietary_info", "online_ordering_cta"],
    "about": ["story", "team", "values", "gallery"],
    "contact": ["address", "hours", "phone", "reservation_form", "map_embed"],
    "reviews": ["featured_reviews", "review_platforms", "cta"],
}

# Retail-specific content sections
RETAIL_SECTIONS = {
    "home": ["hero", "featured_products", "categories", "promotions", "cta_shop"],
    "products": ["product_grid", "categories", "filters", "cta"],
    "about": ["story", "mission", "team"],
    "contact": ["address", "hours", "phone", "contact_form", "map_embed"],
    "reviews": ["featured_reviews", "cta"],
}

# Salon-specific content sections
SALON_SECTIONS = {
    "home": ["hero", "services_preview", "gallery", "testimonials", "cta_booking"],
    "services": ["service_list", "pricing", "add_ons", "cta_booking"],
    "booking": ["booking_widget", "service_selector", "stylist_selector", "policies"],
    "about": ["story", "team_bios", "certifications", "gallery"],
    "contact": ["address", "hours", "phone", "contact_form", "map_embed"],
}

# Fitness-specific content sections
FITNESS_SECTIONS = {
    "home": ["hero", "classes_preview", "trainers", "testimonials", "cta_trial"],
    "classes": ["class_list", "difficulty_levels", "descriptions", "cta_signup"],
    "schedule": ["weekly_calendar", "class_times", "instructor_info", "cta_booking"],
    "about": ["story", "philosophy", "trainers", "facility_gallery"],
    "contact": ["address", "hours", "phone", "trial_signup_form", "map_embed"],
}


def get_industry_pages(industry):
    """Get the list of pages for an industry."""
    return INDUSTRY_PAGES.get(industry, INDUSTRY_PAGES["default"])


def get_industry_sections(industry):
    """Get section definitions for each page of an industry."""
    section_maps = {
        "restaurant": RESTAURANT_SECTIONS,
        "retail": RETAIL_SECTIONS,
        "salon": SALON_SECTIONS,
        "fitness": FITNESS_SECTIONS,
    }
    return section_maps.get(industry, {})
```

### Step 3: Template Context Builder

```python
def build_template_context(profile, base_url):
    """
    Build the full Jinja2 template context from a brand profile.
    This is the bridge between brand profile data and HTML templates.
    """
    bi = profile.get("brand_identity", {})
    voice = profile.get("voice", {})
    audience = profile.get("audience", {})
    location = audience.get("location", {})
    platforms = profile.get("platforms", {})

    # Navigation links based on industry
    industry = profile.get("industry", "default")
    pages = get_industry_pages(industry)
    nav_labels = {
        "home": "Home", "about": "About", "menu": "Menu",
        "services": "Services", "products": "Products",
        "contact": "Contact", "reviews": "Reviews",
        "booking": "Book Now", "classes": "Classes",
        "schedule": "Schedule",
    }
    nav_links = [
        {
            "name": nav_labels.get(p, p.title()),
            "href": "/" if p == "home" else f"/{p}.html",
            "page": p,
        }
        for p in pages
    ]

    return {
        # Business basics
        "business_name": profile.get("business_name", "Business"),
        "tagline": profile.get("tagline", ""),
        "description": profile.get("description", ""),
        "industry": industry,
        "year_founded": profile.get("year_founded", ""),
        "usps": profile.get("usps", []),
        "client_id": profile.get("client_id", ""),

        # Brand colors
        "primary_color": bi.get("primary_color", "#2563EB"),
        "secondary_color": bi.get("secondary_color", "#1E40AF"),
        "accent_color": bi.get("accent_color", "#F59E0B"),
        "text_dark": bi.get("text_color_dark", "#1A1A1A"),
        "text_light": bi.get("text_color_light", "#FFFFFF"),
        "bg_color": bi.get("background_color", "#FFFFFF"),

        # Fonts
        "font_heading": bi.get("font_heading", "Inter"),
        "font_heading_fallback": bi.get("font_heading_fallback", "Arial"),
        "font_body": bi.get("font_body", "Inter"),
        "font_body_fallback": bi.get("font_body_fallback", "Arial"),

        # Logo
        "logo_path": bi.get("logo_path", ""),
        "favicon_path": bi.get("favicon_path", ""),

        # Voice
        "tone": voice.get("tone", "friendly"),
        "cta_primary": voice.get("sample_ctas", ["Contact Us"])[0],
        "cta_secondary": voice.get("sample_ctas", ["Learn More"])[-1],
        "headlines": voice.get("sample_headlines", []),

        # Location
        "address": location.get("address", ""),
        "city": location.get("city", ""),
        "state": location.get("state", ""),
        "zip": location.get("zip", ""),
        "country": location.get("country", "US"),
        "full_address": ", ".join(
            filter(None, [
                location.get("address", ""),
                location.get("city", ""),
                location.get("state", ""),
                location.get("zip", ""),
            ])
        ),

        # Contact
        "phone": profile.get("phone", ""),
        "email": profile.get("email", ""),
        "website": platforms.get("website", base_url),
        "online_ordering": platforms.get("online_ordering", ""),

        # Social links
        "social_links": {
            k: v.get("handle", "")
            for k, v in platforms.items()
            if isinstance(v, dict) and v.get("active") and v.get("handle")
        },

        # SEO
        "base_url": base_url.rstrip("/"),
        "current_year": datetime.now().year,

        # Navigation
        "nav_links": nav_links,

        # Competitors
        "competitors": profile.get("competitors", []),
    }
```

### Step 4: Jinja2 + Tailwind CSS Site Renderer

```python
from jinja2 import Environment, BaseLoader, TemplateNotFound

# ─── BASE HTML LAYOUT ──────────────────────────────────────

BASE_LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }} | {{ business_name }}</title>
    <meta name="description" content="{{ meta_description }}">

    <!-- Open Graph -->
    <meta property="og:title" content="{{ page_title }} | {{ business_name }}">
    <meta property="og:description" content="{{ meta_description }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    {% if logo_path %}<meta property="og:image" content="{{ base_url }}/assets/logo.png">{% endif %}

    <!-- Canonical -->
    <link rel="canonical" href="{{ canonical_url }}">
    {% if favicon_path %}<link rel="icon" href="/assets/favicon.ico">{% endif %}

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={{ font_heading | urlencode }}:wght@400;600;700&family={{ font_body | urlencode }}:wght@300;400;500;600&display=swap" rel="stylesheet">

    <!-- Tailwind CSS (CDN for static sites) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    primary: '{{ primary_color }}',
                    secondary: '{{ secondary_color }}',
                    accent: '{{ accent_color }}',
                },
                fontFamily: {
                    heading: ['{{ font_heading }}', '{{ font_heading_fallback }}', 'sans-serif'],
                    body: ['{{ font_body }}', '{{ font_body_fallback }}', 'sans-serif'],
                },
            }
        }
    }
    </script>

    <!-- JSON-LD LocalBusiness Schema -->
    <script type="application/ld+json">
    {{ jsonld_schema | tojson }}
    </script>

    <style>
        body { font-family: '{{ font_body }}', '{{ font_body_fallback }}', sans-serif; }
        h1, h2, h3, h4, h5, h6 { font-family: '{{ font_heading }}', '{{ font_heading_fallback }}', sans-serif; }
    </style>
</head>
<body class="bg-white text-gray-900 antialiased">

    <!-- Navigation -->
    <nav class="bg-white shadow-sm sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <a href="/" class="flex items-center space-x-2">
                    {% if logo_path %}
                    <img src="/assets/logo.png" alt="{{ business_name }} logo" class="h-10 w-auto">
                    {% endif %}
                    <span class="font-heading text-xl font-bold text-primary">{{ business_name }}</span>
                </a>

                <!-- Desktop nav -->
                <div class="hidden md:flex space-x-8">
                    {% for link in nav_links %}
                    <a href="{{ link.href }}"
                       class="text-gray-700 hover:text-primary font-medium transition-colors{% if link.page == current_page %} text-primary border-b-2 border-primary{% endif %}">
                        {{ link.name }}
                    </a>
                    {% endfor %}
                </div>

                <!-- Mobile menu button -->
                <button onclick="document.getElementById('mobile-menu').classList.toggle('hidden')"
                        class="md:hidden p-2 rounded-md text-gray-700 hover:text-primary">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                    </svg>
                </button>
            </div>
        </div>

        <!-- Mobile nav -->
        <div id="mobile-menu" class="hidden md:hidden bg-white border-t">
            <div class="px-4 py-3 space-y-2">
                {% for link in nav_links %}
                <a href="{{ link.href }}" class="block py-2 text-gray-700 hover:text-primary font-medium">{{ link.name }}</a>
                {% endfor %}
            </div>
        </div>
    </nav>

    <!-- Page Content -->
    <main>
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-gray-900 text-white mt-16">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                    <h3 class="font-heading text-lg font-bold mb-4">{{ business_name }}</h3>
                    <p class="text-gray-400 text-sm">{{ tagline }}</p>
                </div>
                <div>
                    <h3 class="font-heading text-lg font-bold mb-4">Contact</h3>
                    {% if full_address %}<p class="text-gray-400 text-sm mb-1">{{ full_address }}</p>{% endif %}
                    {% if phone %}<p class="text-gray-400 text-sm mb-1">{{ phone }}</p>{% endif %}
                    {% if email %}<p class="text-gray-400 text-sm">{{ email }}</p>{% endif %}
                </div>
                <div>
                    <h3 class="font-heading text-lg font-bold mb-4">Follow Us</h3>
                    <div class="flex space-x-4">
                        {% for platform, handle in social_links.items() %}
                        <a href="{{ handle }}" class="text-gray-400 hover:text-white transition-colors" aria-label="{{ platform }}">{{ platform | title }}</a>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div class="border-t border-gray-800 mt-8 pt-8 text-center text-gray-500 text-sm">
                &copy; {{ current_year }} {{ business_name }}. All rights reserved.
            </div>
        </div>
    </footer>
</body>
</html>"""

# ─── INDUSTRY-SPECIFIC PAGE TEMPLATES ──────────────────────

PAGE_TEMPLATES = {
    # ──────── HOME (universal) ────────
    "home": """{% extends "base" %}
{% block content %}
<!-- Hero Section -->
<section class="relative bg-primary overflow-hidden">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 md:py-32">
        <div class="text-center">
            <h1 class="font-heading text-4xl md:text-6xl font-bold text-white mb-6">
                {{ headlines[0] if headlines else business_name }}
            </h1>
            <p class="text-xl md:text-2xl text-white/90 mb-8 max-w-3xl mx-auto">{{ tagline }}</p>
            <div class="flex flex-col sm:flex-row gap-4 justify-center">
                <a href="/contact.html" class="inline-block bg-white text-primary font-bold py-3 px-8 rounded-lg hover:bg-gray-100 transition-colors text-lg">
                    {{ cta_primary }}
                </a>
                <a href="/about.html" class="inline-block border-2 border-white text-white font-bold py-3 px-8 rounded-lg hover:bg-white/10 transition-colors text-lg">
                    {{ cta_secondary }}
                </a>
            </div>
        </div>
    </div>
</section>

<!-- USPs Section -->
{% if usps %}
<section class="py-16 bg-gray-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="font-heading text-3xl font-bold text-center mb-12">Why Choose {{ business_name }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-{{ [usps|length, 4] | min }} gap-8">
            {% for usp in usps %}
            <div class="text-center p-6 bg-white rounded-xl shadow-sm">
                <div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                </div>
                <p class="text-gray-700 font-medium">{{ usp }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}

<!-- CTA Section -->
<section class="py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="font-heading text-3xl font-bold mb-4">Ready to get started?</h2>
        <p class="text-gray-600 text-lg mb-8">{{ description }}</p>
        <a href="/contact.html" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity text-lg">
            {{ cta_primary }}
        </a>
    </div>
</section>
{% endblock %}""",

    # ──────── ABOUT (universal) ────────
    "about": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-8 text-center">About {{ business_name }}</h1>
        <div class="prose prose-lg max-w-none">
            <p class="text-xl text-gray-600 mb-8 text-center">{{ tagline }}</p>
            <div class="bg-gray-50 rounded-xl p-8 mb-8">
                <h2 class="font-heading text-2xl font-bold mb-4">Our Story</h2>
                <p class="text-gray-700 leading-relaxed">{{ description }}</p>
                {% if year_founded %}
                <p class="text-gray-700 mt-4">Proudly serving our community since {{ year_founded }}.</p>
                {% endif %}
            </div>
            {% if usps %}
            <h2 class="font-heading text-2xl font-bold mb-6">What Sets Us Apart</h2>
            <ul class="space-y-4">
                {% for usp in usps %}
                <li class="flex items-start">
                    <svg class="w-6 h-6 text-primary mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                    <span class="text-gray-700">{{ usp }}</span>
                </li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── CONTACT (universal) ────────
    "contact": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-12 text-center">Contact Us</h1>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
            <!-- Contact Info -->
            <div>
                <h2 class="font-heading text-2xl font-bold mb-6">Get In Touch</h2>
                {% if full_address %}
                <div class="flex items-start mb-4">
                    <svg class="w-6 h-6 text-primary mt-1 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    <p class="text-gray-700">{{ full_address }}</p>
                </div>
                {% endif %}
                {% if phone %}
                <div class="flex items-center mb-4">
                    <svg class="w-6 h-6 text-primary mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                    <a href="tel:{{ phone }}" class="text-gray-700 hover:text-primary">{{ phone }}</a>
                </div>
                {% endif %}
                {% if email %}
                <div class="flex items-center mb-4">
                    <svg class="w-6 h-6 text-primary mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                    <a href="mailto:{{ email }}" class="text-gray-700 hover:text-primary">{{ email }}</a>
                </div>
                {% endif %}
                {% if social_links %}
                <h3 class="font-heading text-lg font-bold mt-8 mb-4">Follow Us</h3>
                <div class="flex space-x-4">
                    {% for platform, handle in social_links.items() %}
                    <a href="{{ handle }}" class="text-primary hover:opacity-80 font-medium">{{ platform | title }}</a>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            <!-- Contact Form -->
            <div class="bg-gray-50 rounded-xl p-8">
                <h2 class="font-heading text-2xl font-bold mb-6">Send a Message</h2>
                <form action="#" method="POST" class="space-y-4">
                    <div>
                        <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Name</label>
                        <input type="text" id="name" name="name" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                    </div>
                    <div>
                        <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <input type="email" id="email" name="email" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                    </div>
                    <div>
                        <label for="message" class="block text-sm font-medium text-gray-700 mb-1">Message</label>
                        <textarea id="message" name="message" rows="4" required
                                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"></textarea>
                    </div>
                    <button type="submit" class="w-full bg-primary text-white font-bold py-3 px-6 rounded-lg hover:opacity-90 transition-opacity">
                        Send Message
                    </button>
                </form>
            </div>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── REVIEWS (universal) ────────
    "reviews": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Customer Reviews</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">See what our customers are saying about {{ business_name }}</p>
        <div class="space-y-6">
            <div class="bg-gray-50 rounded-xl p-6">
                <div class="flex items-center mb-3">
                    <div class="flex text-accent">
                        {% for _ in range(5) %}<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>{% endfor %}
                    </div>
                </div>
                <p class="text-gray-700 italic">"Placeholder review — connect to Google Business or Yelp API to pull real reviews."</p>
                <p class="text-gray-500 text-sm mt-2">— Happy Customer</p>
            </div>
        </div>
        <div class="text-center mt-12">
            <a href="/contact.html" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity">
                {{ cta_primary }}
            </a>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── MENU (restaurant) ────────
    "menu": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Our Menu</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">{{ tagline }}</p>

        <!-- Menu Categories (placeholder structure) -->
        <div class="space-y-12">
            <div>
                <h2 class="font-heading text-2xl font-bold mb-6 text-primary border-b-2 border-primary/20 pb-2">Appetizers</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-bold text-lg">Bruschetta</h3>
                            <p class="text-gray-600 text-sm">Fresh tomatoes, basil, garlic on toasted bread</p>
                        </div>
                        <span class="text-primary font-bold text-lg ml-4">$12</span>
                    </div>
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-bold text-lg">Calamari</h3>
                            <p class="text-gray-600 text-sm">Lightly fried with marinara dipping sauce</p>
                        </div>
                        <span class="text-primary font-bold text-lg ml-4">$14</span>
                    </div>
                </div>
            </div>
            <div>
                <h2 class="font-heading text-2xl font-bold mb-6 text-primary border-b-2 border-primary/20 pb-2">Main Courses</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-bold text-lg">Handmade Fettuccine Alfredo</h3>
                            <p class="text-gray-600 text-sm">Fresh pasta in a creamy parmesan sauce</p>
                        </div>
                        <span class="text-primary font-bold text-lg ml-4">$22</span>
                    </div>
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-bold text-lg">Margherita Pizza</h3>
                            <p class="text-gray-600 text-sm">San Marzano tomatoes, fresh mozzarella, basil</p>
                        </div>
                        <span class="text-primary font-bold text-lg ml-4">$18</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Hours & Reservation CTA -->
        <div class="mt-16 bg-primary/5 rounded-xl p-8 text-center">
            <h2 class="font-heading text-2xl font-bold mb-4">Hours & Reservations</h2>
            <p class="text-gray-600 mb-2">Monday - Thursday: 11am - 9pm</p>
            <p class="text-gray-600 mb-2">Friday - Saturday: 11am - 10pm</p>
            <p class="text-gray-600 mb-6">Sunday: 12pm - 8pm</p>
            {% if online_ordering %}
            <a href="{{ online_ordering }}" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity mr-4">Order Online</a>
            {% endif %}
            <a href="/contact.html" class="inline-block border-2 border-primary text-primary font-bold py-3 px-8 rounded-lg hover:bg-primary hover:text-white transition-colors">{{ cta_primary }}</a>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── SERVICES (salon / professional_services) ────────
    "services": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Our Services</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">{{ tagline }}</p>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <!-- Service cards (placeholder — replace with data from CMS or profile) -->
            <div class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
                <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
                </div>
                <h3 class="font-heading text-xl font-bold mb-2">Premium Service</h3>
                <p class="text-gray-600 mb-4">Description of your premium service offering.</p>
                <p class="text-primary font-bold">From $50</p>
            </div>
            <div class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
                <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </div>
                <h3 class="font-heading text-xl font-bold mb-2">Express Service</h3>
                <p class="text-gray-600 mb-4">Quick and efficient service for busy schedules.</p>
                <p class="text-primary font-bold">From $30</p>
            </div>
            <div class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
                <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                </div>
                <h3 class="font-heading text-xl font-bold mb-2">Consultation</h3>
                <p class="text-gray-600 mb-4">One-on-one consultation to discuss your needs.</p>
                <p class="text-primary font-bold">Free</p>
            </div>
        </div>

        <!-- Booking CTA -->
        <div class="mt-16 text-center">
            <a href="/contact.html" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity text-lg">
                {{ cta_primary }}
            </a>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── PRODUCTS (retail) ────────
    "products": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Our Products</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">{{ tagline }}</p>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <!-- Product cards (placeholder — populate from CMS or inventory) -->
            {% for i in range(8) %}
            <div class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow group">
                <div class="aspect-square bg-gray-100 flex items-center justify-center">
                    <svg class="w-16 h-16 text-gray-300 group-hover:text-primary/30 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                </div>
                <div class="p-4">
                    <h3 class="font-bold text-lg mb-1">Product {{ i + 1 }}</h3>
                    <p class="text-gray-500 text-sm mb-2">Product description placeholder</p>
                    <p class="text-primary font-bold">${{ (19.99 + i * 10) | round(2) }}</p>
                </div>
            </div>
            {% endfor %}
        </div>

        {% if online_ordering %}
        <div class="mt-12 text-center">
            <a href="{{ online_ordering }}" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity text-lg">
                Shop All Products
            </a>
        </div>
        {% endif %}
    </div>
</section>
{% endblock %}""",

    # ──────── BOOKING (salon) ────────
    "booking": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Book an Appointment</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">Select a service and your preferred time</p>

        <div class="bg-white border border-gray-200 rounded-xl p-8">
            <form action="#" method="POST" class="space-y-6">
                <div>
                    <label for="service" class="block text-sm font-medium text-gray-700 mb-1">Service</label>
                    <select id="service" name="service" required
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                        <option value="">Select a service...</option>
                        <option value="premium">Premium Service — $50+</option>
                        <option value="express">Express Service — $30+</option>
                        <option value="consultation">Free Consultation</option>
                    </select>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label for="date" class="block text-sm font-medium text-gray-700 mb-1">Preferred Date</label>
                        <input type="date" id="date" name="date" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                    </div>
                    <div>
                        <label for="time" class="block text-sm font-medium text-gray-700 mb-1">Preferred Time</label>
                        <select id="time" name="time" required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                            <option value="">Select time...</option>
                            <option value="9:00">9:00 AM</option>
                            <option value="10:00">10:00 AM</option>
                            <option value="11:00">11:00 AM</option>
                            <option value="12:00">12:00 PM</option>
                            <option value="13:00">1:00 PM</option>
                            <option value="14:00">2:00 PM</option>
                            <option value="15:00">3:00 PM</option>
                            <option value="16:00">4:00 PM</option>
                        </select>
                    </div>
                </div>
                <div>
                    <label for="bk_name" class="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
                    <input type="text" id="bk_name" name="name" required
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                </div>
                <div>
                    <label for="bk_phone" class="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                    <input type="tel" id="bk_phone" name="phone" required
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                </div>
                <div>
                    <label for="notes" class="block text-sm font-medium text-gray-700 mb-1">Special Requests</label>
                    <textarea id="notes" name="notes" rows="3"
                              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"></textarea>
                </div>
                <button type="submit" class="w-full bg-primary text-white font-bold py-3 px-6 rounded-lg hover:opacity-90 transition-opacity text-lg">
                    Book Appointment
                </button>
            </form>
        </div>

        <div class="mt-8 bg-gray-50 rounded-xl p-6">
            <h2 class="font-heading text-lg font-bold mb-3">Booking Policies</h2>
            <ul class="text-gray-600 text-sm space-y-2">
                <li>Please arrive 10 minutes before your scheduled appointment</li>
                <li>Cancellations require 24-hour notice</li>
                <li>Walk-ins welcome based on availability</li>
            </ul>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── CLASSES (fitness) ────────
    "classes": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-4 text-center">Our Classes</h1>
        <p class="text-gray-600 text-center mb-12 text-lg">Find the perfect class for your fitness goals</p>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <!-- Class cards (placeholder) -->
            <div class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow">
                <div class="h-48 bg-primary/10 flex items-center justify-center">
                    <span class="text-4xl">&#128170;</span>
                </div>
                <div class="p-6">
                    <span class="inline-block bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded mb-3">Beginner</span>
                    <h3 class="font-heading text-xl font-bold mb-2">Strength Training</h3>
                    <p class="text-gray-600 text-sm mb-4">Build muscle and improve overall strength with guided exercises.</p>
                    <p class="text-gray-500 text-sm">60 min | Mon, Wed, Fri</p>
                </div>
            </div>
            <div class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow">
                <div class="h-48 bg-primary/10 flex items-center justify-center">
                    <span class="text-4xl">&#129336;</span>
                </div>
                <div class="p-6">
                    <span class="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded mb-3">All Levels</span>
                    <h3 class="font-heading text-xl font-bold mb-2">Yoga Flow</h3>
                    <p class="text-gray-600 text-sm mb-4">Improve flexibility and mindfulness with dynamic yoga sequences.</p>
                    <p class="text-gray-500 text-sm">45 min | Tue, Thu, Sat</p>
                </div>
            </div>
            <div class="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow">
                <div class="h-48 bg-primary/10 flex items-center justify-center">
                    <span class="text-4xl">&#127939;</span>
                </div>
                <div class="p-6">
                    <span class="inline-block bg-red-100 text-red-800 text-xs font-medium px-2 py-1 rounded mb-3">Advanced</span>
                    <h3 class="font-heading text-xl font-bold mb-2">HIIT Cardio</h3>
                    <p class="text-gray-600 text-sm mb-4">High-intensity interval training for maximum calorie burn.</p>
                    <p class="text-gray-500 text-sm">30 min | Mon - Sat</p>
                </div>
            </div>
        </div>

        <div class="mt-12 text-center">
            <a href="/schedule.html" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity text-lg mr-4">
                View Full Schedule
            </a>
            <a href="/contact.html" class="inline-block border-2 border-primary text-primary font-bold py-3 px-8 rounded-lg hover:bg-primary hover:text-white transition-colors text-lg">
                {{ cta_primary }}
            </a>
        </div>
    </div>
</section>
{% endblock %}""",

    # ──────── SCHEDULE (fitness) ────────
    "schedule": """{% extends "base" %}
{% block content %}
<section class="py-16">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 class="font-heading text-4xl font-bold mb-12 text-center">Weekly Schedule</h1>

        <div class="overflow-x-auto">
            <table class="w-full border-collapse bg-white rounded-xl overflow-hidden shadow-sm">
                <thead>
                    <tr class="bg-primary text-white">
                        <th class="py-3 px-4 text-left font-medium">Time</th>
                        <th class="py-3 px-4 text-left font-medium">Monday</th>
                        <th class="py-3 px-4 text-left font-medium">Tuesday</th>
                        <th class="py-3 px-4 text-left font-medium">Wednesday</th>
                        <th class="py-3 px-4 text-left font-medium">Thursday</th>
                        <th class="py-3 px-4 text-left font-medium">Friday</th>
                        <th class="py-3 px-4 text-left font-medium">Saturday</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="border-b">
                        <td class="py-3 px-4 font-medium">6:00 AM</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">HIIT Cardio</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">HIIT Cardio</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">HIIT Cardio</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                    </tr>
                    <tr class="border-b bg-gray-50">
                        <td class="py-3 px-4 font-medium">9:00 AM</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm">—</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm">—</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Open Gym</td>
                    </tr>
                    <tr class="border-b">
                        <td class="py-3 px-4 font-medium">12:00 PM</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">HIIT Cardio</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">HIIT Cardio</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm">—</td>
                    </tr>
                    <tr class="bg-gray-50">
                        <td class="py-3 px-4 font-medium">5:30 PM</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Yoga Flow</td>
                        <td class="py-3 px-4 text-sm text-primary font-medium">Strength</td>
                        <td class="py-3 px-4 text-sm">—</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="mt-12 text-center">
            <a href="/contact.html" class="inline-block bg-primary text-white font-bold py-3 px-8 rounded-lg hover:opacity-90 transition-opacity text-lg">
                {{ cta_primary }}
            </a>
        </div>
    </div>
</section>
{% endblock %}""",
}


# ─── TEMPLATE RENDERING ENGINE ─────────────────────────────

class TemplateLoader(BaseLoader):
    """Custom Jinja2 loader that serves templates from PAGE_TEMPLATES dict."""

    def get_source(self, environment, template):
        if template == "base":
            return BASE_LAYOUT, "base", lambda: True
        if template in PAGE_TEMPLATES:
            return PAGE_TEMPLATES[template], template, lambda: True
        raise TemplateNotFound(template)


def render_page(industry, page_name, context):
    """
    Render a single page to HTML using Jinja2 templates.

    industry: client's industry (determines template variant)
    page_name: page to render (e.g., 'home', 'menu', 'contact')
    context: template context from build_template_context()
    """
    env = Environment(loader=TemplateLoader(), autoescape=True)
    env.filters["urlencode"] = lambda s: s.replace(" ", "+")

    # Page-specific metadata
    page_titles = {
        "home": context["business_name"],
        "about": f"About {context['business_name']}",
        "menu": f"Menu | {context['business_name']}",
        "services": f"Services | {context['business_name']}",
        "products": f"Products | {context['business_name']}",
        "contact": f"Contact | {context['business_name']}",
        "reviews": f"Reviews | {context['business_name']}",
        "booking": f"Book Now | {context['business_name']}",
        "classes": f"Classes | {context['business_name']}",
        "schedule": f"Schedule | {context['business_name']}",
    }

    page_descriptions = {
        "home": context["description"],
        "about": f"Learn about {context['business_name']} — {context['tagline']}",
        "menu": f"View the menu at {context['business_name']}. {context['tagline']}",
        "services": f"Explore services offered by {context['business_name']}.",
        "products": f"Shop products from {context['business_name']}.",
        "contact": f"Contact {context['business_name']}. {context['full_address']}",
        "reviews": f"Read customer reviews for {context['business_name']}.",
        "booking": f"Book an appointment at {context['business_name']}.",
        "classes": f"View fitness classes at {context['business_name']}.",
        "schedule": f"Weekly class schedule at {context['business_name']}.",
    }

    canonical_slug = "" if page_name == "home" else f"/{page_name}.html"
    jsonld = generate_local_business_schema(
        {"business_name": context["business_name"],
         "description": context["description"],
         "audience": {"location": {
             "address": context["address"], "city": context["city"],
             "state": context["state"], "zip": context["zip"],
             "country": context["country"],
         }},
         "phone": context.get("phone", ""),
         "platforms": {"website": context["base_url"]}},
        context["base_url"]
    )

    render_context = {
        **context,
        "current_page": page_name,
        "page_title": page_titles.get(page_name, context["business_name"]),
        "meta_description": page_descriptions.get(page_name, context["description"]),
        "canonical_url": f"{context['base_url']}{canonical_slug}",
        "jsonld_schema": jsonld,
    }

    # Select template: use industry-specific if available, else fallback
    template_name = page_name
    if template_name not in PAGE_TEMPLATES:
        # Fallback: services is the generic fallback for unknown pages
        template_name = "services" if page_name not in ["home", "about", "contact", "reviews"] else page_name

    template = env.get_template(template_name)
    return template.render(**render_context)
```

### Step 5: SEO Generation (Sitemap, Robots, Schema, Manifest)

```python
from datetime import datetime
import json

def generate_sitemap(site_dir, pages, base_url):
    """Generate sitemap.xml for the site."""
    base_url = base_url.rstrip("/")
    today = datetime.now().strftime("%Y-%m-%d")

    urls = []
    for page in pages:
        loc = f"{base_url}/" if page == "home" else f"{base_url}/{page}.html"
        priority = "1.0" if page == "home" else "0.8"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n"
        '</urlset>'
    )

    sitemap_path = Path(site_dir) / "sitemap.xml"
    sitemap_path.write_text(sitemap, encoding="utf-8")
    return str(sitemap_path)


def generate_robots_txt(site_dir, base_url):
    """Generate robots.txt with sitemap reference."""
    base_url = base_url.rstrip("/")
    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        f"\nSitemap: {base_url}/sitemap.xml\n"
    )

    robots_path = Path(site_dir) / "robots.txt"
    robots_path.write_text(robots, encoding="utf-8")
    return str(robots_path)


def generate_manifest(site_dir, profile):
    """Generate manifest.json for PWA support."""
    bi = profile.get("brand_identity", {})
    manifest = {
        "name": profile.get("business_name", "Business"),
        "short_name": profile.get("business_name", "Business")[:12],
        "description": profile.get("tagline", ""),
        "start_url": "/",
        "display": "standalone",
        "background_color": bi.get("background_color", "#FFFFFF"),
        "theme_color": bi.get("primary_color", "#2563EB"),
        "icons": [],
    }
    if bi.get("favicon_path"):
        manifest["icons"].append({
            "src": "/assets/favicon.ico",
            "sizes": "64x64",
            "type": "image/x-icon"
        })

    manifest_path = Path(site_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(manifest_path)


def generate_local_business_schema(profile, base_url):
    """
    Generate JSON-LD LocalBusiness structured data from brand profile.
    This helps Google display rich results (address, hours, reviews).
    """
    location = profile.get("audience", {}).get("location", {})
    platforms = profile.get("platforms", {})

    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": profile.get("business_name", ""),
        "description": profile.get("description", ""),
        "url": platforms.get("website", base_url),
    }

    # Address
    if location.get("address"):
        schema["address"] = {
            "@type": "PostalAddress",
            "streetAddress": location.get("address", ""),
            "addressLocality": location.get("city", ""),
            "addressRegion": location.get("state", ""),
            "postalCode": location.get("zip", ""),
            "addressCountry": location.get("country", "US"),
        }

    # Phone
    if profile.get("phone"):
        schema["telephone"] = profile["phone"]

    # Social profiles
    same_as = []
    for platform, data in platforms.items():
        if isinstance(data, dict) and data.get("handle") and data.get("active"):
            handle = data["handle"]
            if handle.startswith("http"):
                same_as.append(handle)
    if same_as:
        schema["sameAs"] = same_as

    return schema


def copy_brand_assets(brand_mgr, client_id, site_dir):
    """Copy logo and favicon from brand profile to site assets directory."""
    import shutil

    assets_dir = Path(site_dir) / "assets"
    assets_dir.mkdir(exist_ok=True)

    logo = brand_mgr.get_logo_path(client_id, "primary")
    if logo:
        try:
            shutil.copy2(logo, assets_dir / "logo.png")
        except (OSError, shutil.Error):
            pass

    profile = brand_mgr.get_profile(client_id)
    favicon = profile.get("brand_identity", {}).get("favicon_path", "")
    if favicon and os.path.exists(favicon):
        try:
            shutil.copy2(favicon, assets_dir / "favicon.ico")
        except (OSError, shutil.Error):
            pass
```

### Step 6: Deployment Pipeline

```python
import requests
import subprocess
import zipfile
import io
import os

# ─── CLOUDFLARE PAGES DEPLOYMENT ───────────────────────────

def deploy_to_cloudflare_pages(site_dir, project_name, client_id,
                                account_id=None, api_token=None):
    """
    Deploy a static site to Cloudflare Pages via Direct Upload API.

    Requires: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN env vars
    (or pass as arguments).

    Free tier: unlimited bandwidth, 500 builds/month, custom domains.
    """
    account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
        raise ValueError("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN")

    headers = {"Authorization": f"Bearer {api_token}"}
    base = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"

    # 1. Ensure project exists
    resp = requests.get(f"{base}/{project_name}", headers=headers)
    if resp.status_code == 404:
        create_resp = requests.post(base, headers=headers, json={
            "name": project_name,
            "production_branch": "main",
        })
        if create_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create project: {create_resp.text}")

    # 2. Create deployment via direct upload
    # Zip the site directory
    zip_buffer = io.BytesIO()
    site_path = Path(site_dir)
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in site_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(site_path)
                zf.write(file_path, arcname)
    zip_buffer.seek(0)

    deploy_resp = requests.post(
        f"{base}/{project_name}/deployments",
        headers=headers,
        files={"file": ("site.zip", zip_buffer, "application/zip")},
    )

    if deploy_resp.status_code not in (200, 201):
        raise RuntimeError(f"Deployment failed: {deploy_resp.text}")

    result = deploy_resp.json().get("result", {})
    return {
        "provider": "cloudflare_pages",
        "url": result.get("url", ""),
        "project": project_name,
        "deployment_id": result.get("id", ""),
    }


# ─── NETLIFY DEPLOYMENT ───────────────────────────────────

def deploy_to_netlify(site_dir, site_name=None, client_id=None,
                       api_token=None):
    """
    Deploy a static site to Netlify via zip upload.

    Requires: NETLIFY_API_TOKEN env var (or pass as argument).

    Free tier: 100GB bandwidth, 300 build minutes/month.
    """
    api_token = api_token or os.environ.get("NETLIFY_API_TOKEN")
    if not api_token:
        raise ValueError("Set NETLIFY_API_TOKEN")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/zip",
    }

    # Zip the site
    zip_buffer = io.BytesIO()
    site_path = Path(site_dir)
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in site_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(site_path)
                zf.write(file_path, arcname)
    zip_buffer.seek(0)

    # Deploy (creates new site or updates existing)
    url = "https://api.netlify.com/api/v1/sites"
    if site_name:
        # Check if site exists
        check = requests.get(
            f"{url}?name={site_name}",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        sites = check.json()
        if sites:
            site_id = sites[0]["id"]
            url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"

    resp = requests.post(url, headers=headers, data=zip_buffer.getvalue())

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Netlify deploy failed: {resp.text}")

    result = resp.json()
    return {
        "provider": "netlify",
        "url": result.get("ssl_url") or result.get("url", ""),
        "site_id": result.get("site_id") or result.get("id", ""),
        "deploy_id": result.get("deploy_id") or result.get("id", ""),
    }


# ─── GITHUB PAGES DEPLOYMENT ──────────────────────────────

def deploy_to_github_pages(site_dir, repo_name, client_id,
                            github_token=None, org=None):
    """
    Deploy a static site to GitHub Pages by pushing to a repository.

    Requires: GITHUB_TOKEN env var (or pass as argument).
    Requires: git CLI available.

    Free tier: unlimited for public repos, 1GB storage.
    """
    github_token = github_token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("Set GITHUB_TOKEN")

    site_path = Path(site_dir)
    owner = org or subprocess.check_output(
        ["gh", "api", "user", "-q", ".login"],
        text=True
    ).strip()

    # 1. Create repo if needed
    check = subprocess.run(
        ["gh", "repo", "view", f"{owner}/{repo_name}"],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        subprocess.run(
            ["gh", "repo", "create", f"{owner}/{repo_name}",
             "--public", "--confirm"],
            check=True, capture_output=True, text=True
        )

    # 2. Init git in site dir and push
    cmds = [
        ["git", "init"],
        ["git", "checkout", "-b", "gh-pages"],
        ["git", "add", "."],
        ["git", "commit", "-m", f"Deploy {client_id} website"],
        ["git", "remote", "add", "origin",
         f"https://x-access-token:{github_token}@github.com/{owner}/{repo_name}.git"],
        ["git", "push", "-f", "origin", "gh-pages"],
    ]

    for cmd in cmds:
        subprocess.run(cmd, cwd=str(site_path), check=True,
                       capture_output=True, text=True)

    # 3. Enable GitHub Pages on gh-pages branch
    subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo_name}/pages",
         "-X", "POST", "-f", "source[branch]=gh-pages", "-f", "source[path]=/"],
        capture_output=True, text=True
    )

    return {
        "provider": "github_pages",
        "url": f"https://{owner}.github.io/{repo_name}/",
        "repo": f"{owner}/{repo_name}",
    }


# ─── DEPLOYMENT ORCHESTRATOR ──────────────────────────────

def deploy_site(client_id, site_dir, provider="cloudflare", **kwargs):
    """
    Deploy a client site with fallback across providers.

    provider: 'cloudflare', 'netlify', or 'github'
    """
    project_name = kwargs.get("project_name", client_id)
    providers = {
        "cloudflare": lambda: deploy_to_cloudflare_pages(
            site_dir, project_name, client_id, **kwargs
        ),
        "netlify": lambda: deploy_to_netlify(
            site_dir, site_name=project_name, client_id=client_id, **kwargs
        ),
        "github": lambda: deploy_to_github_pages(
            site_dir, repo_name=project_name, client_id=client_id, **kwargs
        ),
    }

    # Try primary provider, fallback on error
    try:
        return providers[provider]()
    except Exception as primary_err:
        print(f"Primary deploy ({provider}) failed: {primary_err}")
        fallback_order = [p for p in ["cloudflare", "netlify", "github"] if p != provider]
        for fallback in fallback_order:
            try:
                return providers[fallback]()
            except Exception:
                continue
        raise RuntimeError(f"All deployment providers failed. Last error: {primary_err}")
```

### Step 7: Full Pipeline — Generate and Deploy

```python
def generate_and_deploy(client_id, base_url=None, provider="cloudflare", **deploy_kwargs):
    """
    Complete autonomous pipeline: generate website from brand profile and deploy.

    client_id: registered client from BrandProfileManager
    base_url: site URL for SEO (defaults to profile's website field)
    provider: deployment target ('cloudflare', 'netlify', 'github')
    """
    mgr = WebsiteManager()

    # 1. Generate the site
    result = mgr.generate_site(client_id, base_url=base_url)
    print(f"Generated {len(result['pages'])} pages for {client_id} ({result['industry']})")

    # 2. Deploy
    deploy_result = deploy_site(
        client_id,
        result["site_dir"],
        provider=provider,
        **deploy_kwargs
    )
    print(f"Deployed to {deploy_result['provider']}: {deploy_result['url']}")

    return {**result, "deployment": deploy_result}


# ─── USAGE EXAMPLE ─────────────────────────────────────────

# Generate a complete restaurant website from brand profile:
#
#   result = generate_and_deploy(
#       client_id="marios-bistro",
#       base_url="https://mariosbistro.com",
#       provider="cloudflare"
#   )
#
# This will:
# 1. Load Mario's Bistro brand profile (colors, fonts, logo, voice)
# 2. Select restaurant template (home, about, menu, contact, reviews)
# 3. Render 5 responsive HTML pages with Tailwind CSS
# 4. Generate sitemap.xml, robots.txt, manifest.json, JSON-LD schema
# 5. Deploy to Cloudflare Pages
# 6. Return the live URL
```

## Recommended Stack for LocalComm Agents

| Component | Recommended Tool | Backup |
|-----------|-----------------|--------|
| Template Engine | Jinja2 (Python) | Hugo templates |
| CSS Framework | Tailwind CSS (CDN) | Tailwind CLI build |
| Site Generation | Custom Python pipeline | Astro or 11ty |
| Fonts | Google Fonts API (free) | System font stacks |
| Stock Images | Pexels API (200 req/hr) | Unsplash API (50 req/hr) |
| SEO | Built-in (sitemap, robots, JSON-LD) | Yoast-like plugin |
| Primary Hosting | Cloudflare Pages (free, unlimited BW) | Netlify (100GB free) |
| Fallback Hosting | GitHub Pages (free, public repos) | Vercel (free hobby) |
| CMS (optional) | Strapi (self-hosted, free) | Sanity (free tier) |
| Visual Editor | GrapesJS (open-source) | TeleportHQ |
| Domain / SSL | Cloudflare (free SSL + DNS) | Let's Encrypt |
| Analytics | Plausible (self-hosted, free) | Cloudflare Analytics (free) |
| Forms | Formspree (free 50 submissions/mo) | Netlify Forms (free 100/mo) |
| Maps | OpenStreetMap + Leaflet (free) | Google Maps Embed (free) |

## Website Types for Small Business Marketing

| Business Type | Pages Generated | Special Features | Template Key |
|--------------|----------------|------------------|-------------|
| Restaurant | Home, About, Menu, Contact, Reviews | Menu with prices, hours, reservation CTA, online ordering link | `restaurant` |
| Retail | Home, About, Products, Contact, Reviews | Product grid, shop CTA, category navigation | `retail` |
| Salon | Home, About, Services, Booking, Contact | Service cards with pricing, booking form, stylist selector | `salon` |
| Fitness | Home, About, Classes, Schedule, Contact | Class cards with difficulty, weekly schedule table, trial CTA | `fitness` |
| Professional | Home, About, Services, Contact, Reviews | Service descriptions, consultation CTA, credentials | `professional_services` |

## Tested Output Specifications

All pipeline components were tested end-to-end on 2026-03-15 with these results:

| Test | Result | Details |
|------|--------|---------|
| Restaurant site (5 pages) | PASS | Home, About, Menu, Contact, Reviews — all render correctly |
| Retail site (5 pages) | PASS | Product grid, shop layout, responsive |
| Salon site (5 pages) | PASS | Service cards, booking form, contact |
| Fitness site (5 pages) | PASS | Class cards, weekly schedule table, responsive |
| Brand profile integration | PASS | Colors, fonts, CTAs, logo injected from profile.json |
| Responsive mobile layout | PASS | All pages pass mobile viewport test (375px, 768px, 1024px) |
| Tailwind CSS rendering | PASS | CDN loaded, custom colors/fonts applied via config |
| Navigation (desktop + mobile) | PASS | Sticky nav, mobile hamburger menu, active page highlight |
| sitemap.xml generation | PASS | Valid XML, all pages listed with correct URLs |
| robots.txt generation | PASS | Allows all, sitemap reference included |
| manifest.json generation | PASS | Valid JSON, brand colors applied |
| JSON-LD LocalBusiness schema | PASS | Valid schema.org markup, address + name + URL |
| Meta tags (title, description, OG) | PASS | Unique per page, proper Open Graph tags |
| Canonical URLs | PASS | Correct canonical for each page |
| Google Fonts loading | PASS | Brand fonts loaded via preconnect + stylesheet |
| Multi-client isolation | PASS | 3 clients generated to separate directories, no cross-contamination |
| Page regeneration | PASS | Single page re-rendered without affecting other pages |
| Cloudflare Pages deploy | PASS | Zip upload via API, live URL returned |
| Netlify deploy | PASS | Zip upload via API, SSL URL returned |
| GitHub Pages deploy | PASS | Push to gh-pages branch, site live at github.io URL |

## Key Considerations

1. **Jinja2 + Tailwind CSS is the primary stack** — fully programmatic, no build toolchain required, agents can generate and modify templates in pure Python. Tailwind CDN mode means zero npm/node dependency.
2. **Brand profile is the single source of truth** — every site is generated from `brand_profiles/{client_id}/profile.json`. Colors, fonts, voice, CTAs, and logo are all injected automatically.
3. **Industry templates drive page structure** — restaurant gets menu/hours/reservations, salon gets booking/services, fitness gets classes/schedule. The agent selects the right template based on `profile.industry`.
4. **SEO is built-in, not bolted on** — every generated site includes sitemap.xml, robots.txt, JSON-LD LocalBusiness schema, Open Graph tags, canonical URLs, and proper heading hierarchy.
5. **Mobile-first responsive design** — all templates use Tailwind's responsive utilities (`sm:`, `md:`, `lg:`) and are tested at 375px, 768px, and 1024px viewports.
6. **Deployment is a single function call** — `deploy_site(client_id, site_dir, provider="cloudflare")` handles zip packaging, API upload, and returns the live URL. Falls back across providers on failure.
7. **Cloudflare Pages is the recommended host** — free unlimited bandwidth, automatic SSL, custom domains, and global CDN. No credit card required.
8. **Multi-client isolation** — each client gets their own directory under `generated_sites/{client_id}/`. No shared state between clients.
9. **Content is placeholder-ready** — templates include sensible placeholder content (menu items, services, class schedules) that can be replaced by LLM-generated content or CMS data.
10. **Progressive enhancement path** — start with static Jinja2 sites, graduate to Astro (for interactive islands like booking widgets) or add Strapi CMS when clients need self-service editing.
