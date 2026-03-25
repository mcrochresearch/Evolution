---
name: pitch-deck-generation
description: >
  Autonomous pitch deck and presentation generation skill for AI agents. Use when an agent
  needs to create pitch decks, investor presentations, sales decks, business proposals,
  or marketing presentations using free and open-source tools. Covers AI-powered slide
  generation, programmatic PPTX creation, template-based design, and API-driven presentation
  pipelines. Designed for autonomous operation with no human intervention required.
metadata:
  author: localcomm
  version: '1.1'
  updated: '2026-03-15'
---

# Pitch Deck Generation for Autonomous AI Agents

## When to Use This Skill

Use this skill when an AI agent needs to:

- Generate investor pitch decks from business descriptions
- Create sales presentations or proposal decks
- Build marketing presentations for small businesses
- Automate slide deck creation at scale
- Produce branded presentations programmatically via API

## Free Tool Stack (As of March 2026)

### Tier 1: Fully Free / Open-Source (Self-Hosted, API-Ready)

#### 1. Presenton (Best Overall for Autonomous Agents)
- **What**: Open-source AI presentation generator with full REST API
- **License**: Apache 2.0
- **Self-Hosted**: Docker deployment, runs locally
- **API**: Full REST API for programmatic generation
- **LLM Support**: OpenAI, Google Gemini, Ollama (fully offline capable)
- **Image Support**: DALL-E 3, Pexels API (free), or any configured provider
- **Output**: PPTX, PDF
- **Customization**: Custom HTML/Tailwind CSS templates, themes (light, dark, royal_blue, etc.)
- **GitHub**: https://github.com/presenton/presenton
- **Docs**: https://docs.presenton.ai
- **Key Feature**: Upload existing PPTX to create branded templates, then generate on-brand decks

**Quick Start (Docker)**:
```bash
# With Google Gemini (free tier)
docker run -it --name presenton -p 5000:80 \
  -e LLM="google" \
  -e GOOGLE_API_KEY="YOUR_KEY" \
  -e IMAGE_PROVIDER="pexels" \
  -e PEXELS_API_KEY="YOUR_KEY" \
  -v "./app_data:/app_data" \
  ghcr.io/presenton/presenton:latest

# With Ollama (fully offline, no API keys needed)
docker run -it --name presenton -p 5000:80 \
  -e LLM="ollama" \
  -e OLLAMA_MODEL="llama3.2:3b" \
  -e IMAGE_PROVIDER="pexels" \
  -e PEXELS_API_KEY="YOUR_KEY" \
  -v "./app_data:/app_data" \
  ghcr.io/presenton/presenton:latest
```

**API Usage**:
```bash
curl -X POST http://localhost:5000/api/v1/ppt/presentation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Pitch deck for a local restaurant marketing SaaS platform",
    "n_slides": 10,
    "language": "English",
    "template": "general",
    "tone": "sales_pitch",
    "verbosity": "standard",
    "web_search": true,
    "include_title_slide": true,
    "include_table_of_contents": false,
    "export_as": "pptx"
  }'
```

#### 2. python-pptx (Programmatic PPTX Generation)
- **What**: Python library for creating/modifying PowerPoint files
- **License**: MIT
- **Cost**: Completely free
- **Install**: `pip install python-pptx`
- **Best For**: Full programmatic control over slide layouts, charts, images
- **Docs**: https://python-pptx.readthedocs.io

#### 3. slide-deck-ai
- **What**: LLM-powered structured slide generation to PPTX
- **License**: MIT
- **LLM Support**: OpenAI, Azure OpenAI, Google Gemini, Ollama (offline), plus others
- **Features**: PDF content extraction, Pexels image integration, 6 LLM provider support
- **GitHub**: https://github.com/barun-saha/slide-deck-ai
- **Best For**: Quick deck generation from topics or documents

#### 4. Agentic AI PowerPoint Builder (Multi-Agent)
- **What**: LangGraph-based multi-agent system for PPTX generation
- **Agents**: Slide Planner → Content Writer → Visual/Image Agent → PPT Builder
- **Tools**: python-pptx + Unsplash API (free) + LLM
- **Architecture**: True multi-agent workflow with specialized roles
- **Best For**: High-quality automated decks with proper visual sourcing

#### 5. presentation-ai
- **What**: AI presentation generator with real-time slide building
- **Features**: 9+ built-in themes, custom theme creation, AI-generated images, multi-language
- **Stack**: Next.js + Tailwind CSS
- **GitHub**: Part of ALLWEONE AI platform

#### 6. ai-presentation-generator
- **What**: Lightweight generator using Hugging Face models (no API key needed)
- **Output**: PDF, PPTX, HTML
- **Best For**: Zero-config quick drafts
- **Limitation**: Fewer customization options

### Tier 2: Free Tier Cloud Services

#### 7. Gamma (Best Free Cloud Option)
- **What**: AI-powered presentation platform
- **Free Tier**: 400 AI credits at signup, up to 10 cards/prompt
- **Strengths**: Modern web-native design, one-click deck generation
- **Limitations**: Watermark on free tier, limited export formats
- **URL**: https://gamma.app

#### 8. Canva (Magic Design)
- **What**: Design platform with AI presentation features
- **Free Tier**: Core features free, AI generation included
- **Strengths**: Massive template library, brand kit, AI Magic Write
- **Privacy**: Does not train AI on your content
- **API**: Available for enterprise
- **URL**: https://canva.com

#### 9. Google Gemini for Google Slides
- **What**: Native AI integration in Google Workspace
- **Free Tier**: Free with Google account
- **Strengths**: Generates slides, creates images, accesses Google Drive data
- **Best For**: Teams already in Google Workspace

#### 10. Pitch.com
- **What**: Collaborative presentation platform
- **Free Tier**: Up to 5 members, 100 AI credits, branded links/PDFs
- **Strengths**: Real-time collaboration, analytics, branded templates
- **URL**: https://pitch.com

#### 11. Slidebean
- **What**: AI auto-design presentation platform for startups
- **Free Tier**: Unlimited creation, sharing/download requires paid plan ($7/mo starter)
- **Strengths**: 100+ templates, pitch deck structure, investor-focused
- **URL**: https://slidebean.com

#### 12. SlidesAI.io
- **What**: Text-to-Google Slides converter
- **Free Tier**: Supports up to 10 slides
- **Strengths**: Tight Google Workspace integration, royalty-free imagery

#### 13. Venngage
- **What**: AI pitch deck generator with infographic capabilities
- **Free Tier**: Available with basic features
- **Strengths**: Smart charts, bold visuals, typography-focused

### Tier 3: LLM-Assisted Content Generation (Free Tiers)

#### 14. Google AI Studio (Gemini API)
- **What**: Free access to Gemini models for content generation
- **Free Tier**: 15 RPM on Flash models, 1M token context window
- **Use**: Generate slide content, outlines, speaker notes
- **URL**: https://aistudio.google.com

#### 15. Ollama (Fully Local LLMs)
- **What**: Run LLMs locally (Llama 3.2, Mistral, Qwen, etc.)
- **Cost**: Completely free
- **Use**: Generate all presentation content offline
- **URL**: https://ollama.com

#### 16. Genspark
- **What**: AI agent focused on deep web research
- **Free Tier**: Available
- **Use**: Research competitive landscape, market data for pitch decks
- **URL**: https://genspark.ai

## Autonomous Pitch Deck Pipeline Architecture

```
┌────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRATOR                    │
│            (LLM: Gemini/GPT/Ollama/Local)              │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
     ┌──────────▼──────────┐  ┌──────────▼──────────┐
     │   RESEARCH AGENT    │  │   CONTENT AGENT     │
     │   - Market data     │  │   - Slide narrative  │
     │   - Competitor info │  │   - Key metrics      │
     │   - Industry stats  │  │   - Speaker notes    │
     └──────────┬──────────┘  └──────────┬──────────┘
                │                        │
     ┌──────────▼────────────────────────▼──────────┐
     │              STRUCTURE AGENT                   │
     │                                                │
     │  Generates structured JSON:                   │
     │  - Slide order and titles                     │
     │  - Content per slide (bullets, stats)         │
     │  - Chart specifications                       │
     │  - Image search keywords                      │
     │  - Design preferences                         │
     └──────────────────────┬────────────────────────┘
                            │
     ┌──────────────────────▼────────────────────────┐
     │            VISUAL ASSET AGENT                  │
     │                                                │
     │  - Charts/graphs: matplotlib / python-pptx    │
     │  - Images: Pexels API (free) / Unsplash       │
     │  - AI images: FLUX Schnell / Gemini Imagen    │
     │  - Icons: Iconify API (free)                  │
     └──────────────────────┬────────────────────────┘
                            │
     ┌──────────────────────▼────────────────────────┐
     │           PPTX BUILDER AGENT                   │
     │                                                │
     │  Option A: Presenton API (best)               │
     │  Option B: python-pptx (full control)         │
     │  Option C: slide-deck-ai                      │
     │                                                │
     │  - Apply branded template                     │
     │  - Insert content and visuals                 │
     │  - Format layouts consistently                │
     │  - Export PPTX and PDF                        │
     └──────────────────────┬────────────────────────┘
                            │
     ┌──────────────────────▼────────────────────────┐
     │              OUTPUT & QA                       │
     │                                                │
     │  - Validate slide count and content           │
     │  - Check image placement                      │
     │  - Verify brand consistency                   │
     │  - Export final PPTX + PDF                    │
     └──────────────────────────────────────────────┘
```

## Implementation Guide

### Step 1: Generate Pitch Deck Structure (LLM Agent)

```python
import json

PITCH_DECK_TEMPLATE = {
    "title": "",
    "subtitle": "",
    "company_name": "",
    "slides": [
        {"type": "title", "title": "", "subtitle": ""},
        {"type": "problem", "title": "The Problem", "bullets": [], "image_keyword": ""},
        {"type": "solution", "title": "Our Solution", "bullets": [], "image_keyword": ""},
        {"type": "market", "title": "Market Opportunity", "stats": [], "chart": {}},
        {"type": "product", "title": "How It Works", "bullets": [], "image_keyword": ""},
        {"type": "traction", "title": "Traction", "metrics": [], "chart": {}},
        {"type": "business_model", "title": "Business Model", "bullets": [], "chart": {}},
        {"type": "competition", "title": "Competitive Landscape", "competitors": []},
        {"type": "team", "title": "Our Team", "members": []},
        {"type": "ask", "title": "The Ask", "funding_amount": "", "use_of_funds": []}
    ],
    "design": {
        "primary_color": "#2563EB",
        "secondary_color": "#1E40AF",
        "accent_color": "#F59E0B",
        "font_heading": "Calibri",
        "font_body": "Calibri",
        "theme": "professional"
    }
}
```

### Step 2: Build Deck with Presenton API

```python
import requests

PRESENTON_URL = "http://localhost:5000"

def generate_pitch_deck(business_description, n_slides=10, tone="sales_pitch"):
    """Generate a complete pitch deck using Presenton API"""
    response = requests.post(
        f"{PRESENTON_URL}/api/v1/ppt/presentation/generate",
        json={
            "content": business_description,
            "n_slides": n_slides,
            "language": "English",
            "template": "general",
            "tone": tone,
            "verbosity": "standard",
            "web_search": True,
            "include_title_slide": True,
            "export_as": "pptx"
        }
    )
    result = response.json()
    pptx_url = f"{PRESENTON_URL}{result['path']}"
    edit_url = f"{PRESENTON_URL}{result['edit_path']}"
    return {
        "presentation_id": result["presentation_id"],
        "download_url": pptx_url,
        "edit_url": edit_url
    }
```

### Step 3: Build Deck with python-pptx (Full Control Alternative)

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
import matplotlib.pyplot as plt
import io

def create_pitch_deck(deck_data, output_path):
    """Create a professional pitch deck using python-pptx"""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    design = deck_data["design"]
    primary = RGBColor.from_string(design["primary_color"].lstrip("#"))

    for slide_data in deck_data["slides"]:
        if slide_data["type"] == "title":
            slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
            _add_title_slide(slide, slide_data, primary, prs)
        elif slide_data["type"] in ["problem", "solution", "product"]:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _add_content_slide(slide, slide_data, primary, prs)
        elif slide_data["type"] in ["market", "traction", "business_model"]:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _add_chart_slide(slide, slide_data, primary, prs)
        elif slide_data["type"] == "competition":
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _add_competition_slide(slide, slide_data, primary, prs)
        elif slide_data["type"] == "team":
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _add_team_slide(slide, slide_data, primary, prs)
        elif slide_data["type"] == "ask":
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _add_ask_slide(slide, slide_data, primary, prs)

    prs.save(output_path)
    return output_path

def _add_title_slide(slide, data, primary, prs):
    """Add a branded title slide"""
    # Background
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = primary

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(1), Inches(2.5), Inches(11), Inches(2)
    )
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = data["title"]
    p.font.size = Pt(44)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    # Subtitle
    p2 = tf.add_paragraph()
    p2.text = data.get("subtitle", "")
    p2.font.size = Pt(24)
    p2.font.color.rgb = RGBColor(220, 220, 220)
    p2.alignment = PP_ALIGN.CENTER

def _add_content_slide(slide, data, primary, prs):
    """Add a content slide with bullets and optional image"""
    # Header bar
    header_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), prs.slide_width, Inches(1.2)
    )
    header_bar.fill.solid()
    header_bar.fill.fore_color.rgb = primary
    header_bar.line.fill.background()

    # Title text on header bar
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.2), Inches(12), Inches(0.8)
    )
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = data["title"]
    p.font.size = Pt(32)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True

    # Bullets
    content_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.5), Inches(6), Inches(5)
    )
    tf = content_box.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(data.get("bullets", [])):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = f"• {bullet}"
        p.font.size = Pt(18)
        p.space_after = Pt(12)

def _generate_chart_image(chart_data, output_path):
    """Generate a chart image using matplotlib"""
    fig, ax = plt.subplots(figsize=(8, 5))
    chart_type = chart_data.get("type", "bar")

    if chart_type == "bar":
        ax.bar(chart_data["labels"], chart_data["values"], color="#2563EB")
    elif chart_type == "pie":
        ax.pie(chart_data["values"], labels=chart_data["labels"], autopct="%1.0f%%")
    elif chart_type == "line":
        ax.plot(chart_data["labels"], chart_data["values"], marker="o", color="#2563EB")
        ax.fill_between(range(len(chart_data["values"])), chart_data["values"], alpha=0.3, color="#2563EB")

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_title(chart_data.get("title", ""), fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight", transparent=True)
    plt.close()
    return output_path

def _add_competition_slide(slide, data, primary, prs):
    """Add a competition table slide"""
    # Header bar
    header_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), prs.slide_width, Inches(1.2)
    )
    header_bar.fill.solid()
    header_bar.fill.fore_color.rgb = primary
    header_bar.line.fill.background()

    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.2), Inches(12), Inches(0.8)
    )
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = data["title"]
    p.font.size = Pt(32)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True

    # Competition table
    competitors = data.get("competitors", [])
    if competitors:
        rows = len(competitors) + 1
        cols = 4
        table_shape = slide.shapes.add_table(rows, cols,
            Inches(0.5), Inches(1.5), Inches(12), Inches(5))
        table = table_shape.table

        # Header row
        headers = ["Company", "Strengths", "Weaknesses", "Differentiator"]
        for j, header in enumerate(headers):
            cell = table.cell(0, j)
            cell.text = header
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.bold = True
                paragraph.font.color.rgb = RGBColor(255, 255, 255)
                paragraph.font.size = Pt(14)
            cell.fill.solid()
            cell.fill.fore_color.rgb = primary

        # Data rows with alternating colors
        for i, comp in enumerate(competitors):
            row_idx = i + 1
            values = [
                comp.get("name", ""),
                comp.get("strengths", ""),
                comp.get("weaknesses", ""),
                comp.get("differentiator", "")
            ]
            for j, val in enumerate(values):
                cell = table.cell(row_idx, j)
                cell.text = val
                for paragraph in cell.text_frame.paragraphs:
                    paragraph.font.size = Pt(12)
                # Alternating row colors
                if row_idx % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(240, 245, 255)

def _add_team_slide(slide, data, primary, prs):
    """Add a team slide with member cards"""
    # Header bar
    header_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), prs.slide_width, Inches(1.2)
    )
    header_bar.fill.solid()
    header_bar.fill.fore_color.rgb = primary
    header_bar.line.fill.background()

    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.2), Inches(12), Inches(0.8)
    )
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = data["title"]
    p.font.size = Pt(32)
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.font.bold = True

    # Team member cards (3-column layout)
    members = data.get("members", [])
    card_width = Inches(3.5)
    card_height = Inches(4.5)
    start_x = Inches(0.8)
    start_y = Inches(1.8)
    gap = Inches(0.5)

    for i, member in enumerate(members[:3]):  # Max 3 per row
        x = start_x + i * (card_width + gap)
        # Card background
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            x, start_y, card_width, card_height
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(245, 247, 255)
        card.line.color.rgb = RGBColor(200, 210, 230)

        # Member name
        name_box = slide.shapes.add_textbox(
            x + Inches(0.2), start_y + Inches(0.5), card_width - Inches(0.4), Inches(0.5)
        )
        tf = name_box.text_frame
        p = tf.paragraphs[0]
        p.text = member.get("name", "")
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = primary
        p.alignment = PP_ALIGN.CENTER

        # Role
        role_box = slide.shapes.add_textbox(
            x + Inches(0.2), start_y + Inches(1.0), card_width - Inches(0.4), Inches(0.4)
        )
        tf = role_box.text_frame
        p = tf.paragraphs[0]
        p.text = member.get("role", "")
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(100, 100, 100)
        p.alignment = PP_ALIGN.CENTER
```

### Step 4: Source Free Images

```python
import requests

def search_pexels_images(query, per_page=3):
    """Search Pexels for free stock images (free API key required)"""
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page, "orientation": "landscape"}
    )
    photos = response.json().get("photos", [])
    return [{"url": p["src"]["large"], "alt": p["alt"]} for p in photos]

def search_unsplash_images(query, per_page=3):
    """Search Unsplash for free stock images"""
    response = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
        params={"query": query, "per_page": per_page, "orientation": "landscape"}
    )
    results = response.json().get("results", [])
    return [{"url": r["urls"]["regular"], "alt": r["alt_description"]} for r in results]
```

## Recommended Stack for LocalComm Agents

| Component | Recommended Tool | Backup |
|-----------|-----------------|--------|
| Deck Generation | Presenton API (self-hosted) | python-pptx (programmatic) |
| Content/Narrative | Gemini API (free tier) | Ollama + local LLM |
| Research Data | Genspark (free) | Web search APIs |
| Stock Images | Pexels API (free) | Unsplash API (free) |
| AI Images | FLUX Schnell (free API) | Pexels fallback |
| Charts/Graphs | matplotlib | python-pptx native charts |
| Export Format | PPTX + PDF | Google Slides (via API) |

## Pitch Deck Types Supported

1. **Investor Pitch Deck**: Problem → Solution → Market → Product → Traction → Business Model → Competition → Team → Ask
2. **Sales Deck**: Challenge → Solution → Features → Case Studies → Pricing → CTA
3. **Business Proposal**: Overview → Scope → Approach → Timeline → Budget → Team → Next Steps
4. **Marketing Presentation**: Situation → Strategy → Tactics → Budget → KPIs → Timeline
5. **Restaurant/Local Business Deck**: About → Menu Highlights → Location → Reviews → Specials → Contact

## Tested Output Specifications

All pipeline components were tested end-to-end on 2026-03-15 with these results:

| Test | Result | Details |
|------|--------|---------|
| Full 10-slide pitch deck | PASS | 192KB PPTX, 10 slides |
| Title slide (branded bg) | PASS | Solid color fill verified |
| Content slides (bullets) | PASS | Proper font sizing and spacing |
| Chart slides (matplotlib) | PASS | Bar, line, pie charts embedded as images |
| Competition table | PASS | 4-column table with styled header row |
| Team cards | PASS | Rounded rectangle cards, 3-column layout |
| Ask slide | PASS | Large funding amount, use-of-funds bullets |
| Bar chart generation | PASS | 12KB PNG at 200 DPI |
| Line chart generation | PASS | 27KB PNG with fill |
| Pie chart generation | PASS | 22KB PNG with percentage labels |

## Key Considerations

1. **Presenton is the top choice** for autonomous agents — it's the only open-source tool with both a REST API and self-hosted deployment, supporting fully offline operation via Ollama.
2. **python-pptx gives maximum control** when you need pixel-perfect layouts or custom slide types that templates don't cover.
3. **Brand consistency**: Upload an existing PPTX to Presenton to create a template, then all generated decks inherit that design.
4. **Free image APIs**: Pexels (200 requests/hour) and Unsplash (50 requests/hour) are both free with attribution.
5. **Offline capability**: Presenton + Ollama + Pexels can run entirely without paid API keys (except Pexels needs a free key).
6. **Chart quality**: Use matplotlib to pre-render charts as images rather than relying on AI to generate chart visuals (AI hallucinates numbers).
7. **Rate limits**: Gemini free tier allows 15 RPM on Flash models. Build queuing into your pipeline for batch deck generation.
