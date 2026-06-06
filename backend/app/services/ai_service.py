"""AI Service Layer — extracted from routers/content.py, routers/other.py, app/core/dependencies.py"""
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import AIModel, SystemSettings, AIProxy, ContentProvider, ContentGeneration, ContentSession
from app.core.dependencies import (
    NINE_ROUTER_DB, NINE_ROUTER_URL, NINE_ROUTER_API_KEY,
    COMBO_DISPLAY_NAMES, get_fonnte_token, _send_fonnte_sync,
)


# ─── 9router Combo helpers ────────────────────────────────────────────────────

def get_9router_combos() -> list[dict]:
    """Return list of active combo dicts from 9router SQLite or HTTP fallback."""
    try:
        import sqlite3 as _sqlite3
        con = _sqlite3.connect(NINE_ROUTER_DB, timeout=2)
        rows = con.execute("SELECT name FROM combos WHERE active=1 OR active IS NULL ORDER BY name").fetchall()
        con.close()
        if rows:
            return [{"name": r[0], "display_name": COMBO_DISPLAY_NAMES.get(r[0], r[0])} for r in rows]
    except Exception as e:
        print(f"[9router] sqlite query failed: {e}", flush=True)
    try:
        import httpx as _httpx
        url = f"{NINE_ROUTER_URL.rstrip('/')}/models"
        with _httpx.Client(timeout=3) as client:
            r = client.get(url, headers={"Authorization": f"Bearer {NINE_ROUTER_API_KEY}"})
        if r.status_code == 200:
            data = r.json()
            models = data.get("data") if isinstance(data, dict) else data
            if isinstance(models, list):
                names = [m["id"] if isinstance(m, dict) else str(m) for m in models]
                names = [n for n in names if n.startswith("combo-")] or names
                return [{"name": n, "display_name": COMBO_DISPLAY_NAMES.get(n, n)} for n in names]
    except Exception as e:
        print(f"[9router] /v1/models fallback failed: {e}", flush=True)
    return [{"name": k, "display_name": v} for k, v in COMBO_DISPLAY_NAMES.items()]


def _get_active_combo(db: Session) -> str:
    row = db.query(SystemSettings).filter_by(key="ai_active_combo").first()
    return (row.value if row and row.value else "combo-kiro")


def _get_proxy_url(db: Session) -> str:
    row = db.query(SystemSettings).filter_by(key="ai_proxy_url").first()
    return (row.value if row and row.value else NINE_ROUTER_URL).rstrip("/")


def set_active_combo(db: Session, combo: str) -> None:
    row = db.query(SystemSettings).filter_by(key="ai_active_combo").first()
    if row:
        row.value = combo
    else:
        db.add(SystemSettings(key="ai_active_combo", value=combo))


def set_proxy_url(db: Session, url: str) -> None:
    row = db.query(SystemSettings).filter_by(key="ai_proxy_url").first()
    if row:
        row.value = url
    else:
        db.add(SystemSettings(key="ai_proxy_url", value=url))


# ─── Feature Defaults ─────────────────────────────────────────────────────────

def _get_feature_defaults(db: Session) -> dict:
    row = db.query(SystemSettings).filter_by(key="ai_feature_defaults").first()
    if row and row.value:
        try:
            data = json.loads(row.value)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def set_feature_defaults(db: Session, defaults: dict) -> dict:
    valid_features = {"chat", "article", "image", "analysis", "caption"}
    valid_combos = {c["name"] for c in get_9router_combos()}
    cleaned: dict[str, str] = {}
    for feature, combo in defaults.items():
        if feature not in valid_features:
            continue
        combo_str = (combo or "").strip()
        if combo_str and combo_str not in valid_combos:
            raise ValueError(f"Combo '{combo_str}' tidak valid untuk fitur '{feature}'")
        cleaned[feature] = combo_str
    value = json.dumps(cleaned)
    row = db.query(SystemSettings).filter_by(key="ai_feature_defaults").first()
    if row:
        row.value = value
    else:
        db.add(SystemSettings(key="ai_feature_defaults", value=value))
    return cleaned


# ─── AI Proxy CRUD ─────────────────────────────────────────────────────────────

def list_ai_proxies(db: Session) -> list[AIProxy]:
    return db.query(AIProxy).order_by(AIProxy.created_at.asc()).all()


def create_ai_proxy(db: Session, name: str, base_url: str, api_key: str, model: str, feature: str) -> AIProxy:
    proxy = AIProxy(name=name, base_url=base_url.rstrip("/"), api_key=api_key, model=model, feature=feature)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


def update_ai_proxy(db: Session, proxy_id: str, updates: dict) -> AIProxy:
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise ValueError("Proxy tidak ditemukan")
    for key in ("name", "base_url", "api_key", "model", "feature"):
        if key in updates:
            val = updates[key]
            if key == "base_url" and val:
                val = val.rstrip("/")
            setattr(proxy, key, val)
    db.commit()
    db.refresh(proxy)
    return proxy


def activate_ai_proxy(db: Session, proxy_id: str) -> AIProxy:
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise ValueError("Proxy tidak ditemukan")
    db.query(AIProxy).filter(AIProxy.feature == proxy.feature).update({"is_active": False})
    proxy.is_active = True
    db.commit()
    db.refresh(proxy)
    return proxy


def delete_ai_proxy(db: Session, proxy_id: str) -> None:
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise ValueError("Proxy tidak ditemukan")
    db.delete(proxy)
    db.commit()


# ─── AI Model registry ────────────────────────────────────────────────────────

def get_default_model(db: Session, capability: str) -> Optional[AIModel]:
    field = f"is_default_{capability}"
    return db.query(AIModel).filter(getattr(AIModel, field) == 1, AIModel.is_active == 1).first()


def _ai_model_to_out(m) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "model_id": m.model_id,
        "description": m.description,
        "capabilities": json.loads(m.capabilities) if m.capabilities else [],
        "is_active": m.is_active,
        "is_default_chat": bool(m.is_default_chat),
        "is_default_image": bool(m.is_default_image),
        "is_default_article": bool(m.is_default_article),
        "is_default_analysis": bool(m.is_default_analysis),
    }


# ─── AI Config resolver ────────────────────────────────────────────────────────

def get_proxy_for_feature(db: Session, feature: str) -> Optional[AIProxy]:
    proxy = db.query(AIProxy).filter(AIProxy.feature == feature, AIProxy.is_active == True).first()
    if not proxy:
        proxy = db.query(AIProxy).filter(AIProxy.is_active == True, AIProxy.feature.is_(None)).first()
    return proxy


def get_ai_config(db: Session, capability: str = "chat") -> dict:
    """Per-feature AIProxy first, fallback to 9router. Optional model override per capability via ai_models registry."""
    proxy = get_proxy_for_feature(db, capability)
    if proxy:
        provider = proxy.provider or "openai"
        # Map api_key to the correct provider key
        cfg = {
            "provider": provider,
            "base_url": proxy.base_url.rstrip("/"),
            "model": proxy.model,
        }
        # Map api_key based on provider type
        if provider == "gemini":
            cfg["gemini_key"] = proxy.api_key
            cfg["openai_key"] = ""
            cfg["claude_key"] = ""
        elif provider == "claude":
            cfg["claude_key"] = proxy.api_key
            cfg["openai_key"] = ""
            cfg["gemini_key"] = ""
        else:  # openai or openai-compatible
            cfg["openai_key"] = proxy.api_key
            cfg["gemini_key"] = ""
            cfg["claude_key"] = ""
    else:
        cfg = get_9router_config(db)
    default_model = get_default_model(db, capability)
    if default_model and default_model.model_id:
        cfg["model"] = default_model.model_id
    return cfg


def get_9router_config(db: Session, feature: Optional[str] = None) -> dict:
    model = _get_active_combo(db)
    provider = "openai"  # 9router is OpenAI-compatible by default
    if feature:
        defaults = _get_feature_defaults(db)
        override = (defaults.get(feature) or "").strip()
        if override:
            model = override
    # Check for provider override in system settings
    provider_row = db.query(SystemSettings).filter_by(key="ai_default_provider").first()
    if provider_row and provider_row.value:
        provider = provider_row.value
    return {
        "provider": provider,
        "openai_key": NINE_ROUTER_API_KEY,
        "base_url": _get_proxy_url(db),
        "model": model,
        "gemini_key": "",
        "claude_key": "",
    }


# ─── AI Sync call ─────────────────────────────────────────────────────────────

def call_ai_sync(prompt: str, config: dict, httpx_module) -> str:
    """Synchronous HTTP call to gemini/claude/openai."""
    provider = config["provider"]
    with httpx_module.Client(timeout=120) as client:
        if provider == "gemini":
            if not config["gemini_key"]:
                raise Exception("Gemini API Key belum dikonfigurasi.")
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={"x-goog-api-key": config["gemini_key"]},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "claude":
            if not config["claude_key"]:
                raise Exception("Claude API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "claude-haiku-4-5-20251001"
            url = f"{base_url.rstrip('/')}/chat/completions"
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {config['claude_key']}", "Content-Type": "application/json"},
                json={"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code != 200:
                raise Exception(f"Claude API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        elif provider == "openai":
            if not config["openai_key"]:
                raise Exception("OpenAI API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "gpt-4o-mini"
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {config['openai_key']}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024},
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Provider '{provider}' tidak dikenali.")


# ─── Prompt builders ─────────────────────────────────────────────────────────

def build_analysis_prompt(lead, product_list: str) -> str:
    return f"""Kamu adalah konsultan digital marketing untuk UMKM Indonesia. Analisa bisnis berikut dan berikan insight yang persuasif dan mudah dipahami pemilik usaha.

DATA BISNIS:
- Nama: {lead.business_name}
- Alamat: {lead.address or 'Tidak diketahui'}
- Rating Google: {lead.rating}/5
- Kategori: {lead.product_interest or 'Umum'}

PRODUK/LAYANAN YANG KAMI TAWARKAN:
{product_list}

INSTRUKSI:
Berikan output dalam format JSON berikut (Bahasa Indonesia, gaya bicara santai tapi profesional):
{{
  "pain_points": ["masalah 1 yang spesifik dan relatable untuk pemilik usaha", "masalah 2", "masalah 3"],
  "suggested_product": "nama produk kami yang paling cocok",
  "approach_message": "satu paragraf pendek pesan WA yang bisa langsung dikirim ke pemilik bisnis ini, persuasif tapi tidak memaksa, sebutkan masalah mereka dan solusi kita"
}}

PENTING: Pain points harus spesifik ke bisnis ini, bukan generik. Pesan pendekatan harus terasa personal."""


def parse_ai_response(text: str) -> dict:
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass
    return {"pain_points": [text], "suggested_product": "", "approach_message": ""}


def build_caption_system_message(platform: str, tone: str) -> str:
    platform_guide = {
        "instagram": "Instagram: max 2200 karakter, 3-5 hashtag relevan, emoji secukupnya, CTA di akhir.",
        "tiktok": "TikTok: singkat dan catchy, hook kuat di kalimat pertama, 5-10 hashtag trending.",
    }.get(platform, "")
    return (
        f"Kamu adalah content writer media sosial profesional Bahasa Indonesia. "
        f"Buat caption {platform.upper()} yang engaging, tone: '{tone}'. {platform_guide} "
        f"WAJIB return valid JSON: {{\"caption\": \"...\", \"hashtags\": [\"#tag\"], \"notes\": \"tip singkat\"}}"
    )


def parse_caption_response(text: str) -> dict:
    m = re.search(r'\{[\s\S]*\}', text)
    try:
        return json.loads(m.group()) if m else {"caption": text, "hashtags": [], "notes": ""}
    except Exception:
        return {"caption": text, "hashtags": [], "notes": ""}


def parse_seo_article_response(text: str, keyword: str) -> dict:
    def _parse_delimited(t: str) -> dict:
        title = re.search(r'^TITLE:\s*(.+)', t, re.MULTILINE) or re.search(r'', t)
        meta = re.search(r'^META:\s*(.+)', t, re.MULTILINE)
        fk = re.search(r'^FOCUS_KEYWORD:\s*(.+)', t, re.MULTILINE)
        sk = re.search(r'^SECONDARY_KEYWORDS:\s*(.+)', t, re.MULTILINE)
        body_m = re.search(r'---ARTICLE---([\s\S]*?)---END---', t)
        return {
            "title": title.group(1).strip() if title and title.lastindex else f"Panduan Lengkap: {keyword}",
            "meta_description": meta.group(1).strip() if meta else "",
            "focus_keyword": fk.group(1).strip() if fk else keyword,
            "secondary_keywords": [k.strip() for k in sk.group(1).split(",") if k.strip()] if sk else [],
            "body": body_m.group(1).strip() if body_m else t,
        }
    return _parse_delimited(text)


# ─── Context helpers (for caption/article generation) ───────────────────────

def _get_session_ctx(session_id: Optional[str], db: Session) -> Optional[str]:
    if not session_id:
        return None
    session = db.query(ContentSession).filter(ContentSession.id == session_id).first()
    gens = db.query(ContentGeneration).filter(
        ContentGeneration.session_id == session_id
    ).order_by(ContentGeneration.created_at.desc()).limit(5).all()
    if not gens:
        return None
    parts = []
    for g in reversed(gens):
        try:
            inp = json.loads(g.input_data) if g.input_data else {}
        except Exception:
            inp = {}
        if isinstance(inp, dict):
            topic = inp.get("topic", "")
            keywords = inp.get("keywords", [])
            kw_str = f", keyword: {', '.join(keywords)}" if keywords else ""
            parts.append(f"[{g.tool_type}]: {topic}{kw_str}")
    return "\n".join(parts) if parts else None


def _get_manual_ctx(context_from: list, db: Session) -> Optional[str]:
    if not context_from:
        return None
    gens = db.query(ContentGeneration).filter(
        ContentGeneration.id.in_(context_from)
    ).all()
    parts = []
    for g in gens:
        try:
            out = json.loads(g.output_data) if g.output_data else {}
        except Exception:
            out = {}
        if isinstance(out, dict):
            caption = out.get("caption") or out.get("body") or out.get("title") or ""
            if caption:
                parts.append(f"[{g.tool_type}]: {caption[:200]}")
    return "\n".join(parts) if parts else None


# ─── Caption generation ───────────────────────────────────────────────────────

def generate_caption(
    db: Session,
    user_id: int,
    topic: str,
    platform: str,
    tone: str,
    keywords: list[str],
    session_id: Optional[str],
    context_from: Optional[list[str]],
) -> dict:
    """Full caption generation pipeline."""
    ai = get_ai_config(db, "caption")
    if not ai.get("openai_key"):
        raise ValueError("API Key AI belum dikonfigurasi di Settings")

    system_msg = build_caption_system_message(platform, tone)
    user_msg = f"Topik: {topic}"
    if keywords:
        user_msg += f"\nKeyword wajib disebut: {', '.join(keywords)}"
    ctx = _get_session_ctx(session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    import httpx as _httpx
    gen = ContentGeneration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        tool_type="caption",
        input_data=json.dumps({
            "topic": topic, "platform": platform, "tone": tone, "keywords": keywords,
        }),
        model_used=ai.get("model", ""),
        provider_name="System AI",
        status="pending",
    )
    db.add(gen)
    db.commit()

    try:
        text = _call_caption(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["openai_key"],
            base_url=ai.get("base_url", ""),
            model=ai.get("model", "gpt-4o-mini"),
            max_tokens=800,
        )
        result = parse_caption_response(text)
        gen.output_data = json.dumps(result)
        gen.status = "done"
        db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}
    except Exception as e:
        gen.status = "error"
        gen.error_msg = str(e)
        db.commit()
        raise ValueError(f"Gagal generate caption: {e}")


def _call_caption(messages: list, api_key: str, base_url: str, model: str, max_tokens: int) -> str:
    """Call OpenAI-compatible endpoint for caption generation."""
    import httpx as _httpx
    url = f"{base_url.rstrip('/')}/chat/completions"
    with _httpx.Client(timeout=120) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": max_tokens, "messages": messages},
        )
        if resp.status_code != 200:
            raise Exception(f"AI call failed: {resp.status_code} - {resp.text[:200]}")
        return resp.json()["choices"][0]["message"]["content"]


# ─── SEO Article generation ───────────────────────────────────────────────────

def generate_seo_article(
    db: Session,
    user_id: int,
    keyword: str,
    title: Optional[str],
    word_count: int,
    tone: str,
    search_intent: Optional[str],
    keyword_difficulty: Optional[float],
    search_volume: Optional[int],
    lsi_keywords: Optional[list[str]],
    faq_topics: Optional[list[str]],
    serp_features: Optional[list[str]],
    target_audience: Optional[str],
    target_location: Optional[str],
    brand_name: Optional[str],
    unique_angle: Optional[str],
    internal_link_targets: Optional[str],
    session_id: Optional[str],
    context_from: Optional[list[str]],
) -> dict:
    """Full SEO article generation pipeline."""
    ai = get_ai_config(db, "article")
    if not ai.get("openai_key"):
        raise ValueError("API Key AI belum dikonfigurasi di Settings")

    target_title = title or f"Panduan Lengkap: {keyword}"

    intent_guide = {
        "informational": "Search intent INFORMATIONAL: edukasi pembaca, jawab 'apa', 'bagaimana', 'mengapa'. Buat artikel komprehensif dengan definisi jelas, contoh praktis, dan takeaway.",
        "commercial": "Search intent COMMERCIAL INVESTIGATION: pembaca sedang membandingkan pilihan. Sertakan perbandingan, pro-kontra, kriteria pemilihan, dan rekomendasi konkret.",
        "transactional": "Search intent TRANSACTIONAL: pembaca siap bertindak. CTA kuat, benefit produk/jasa menonjol, hilangkan keraguan, sertakan social proof.",
        "navigational": "Search intent NAVIGATIONAL: bantu user menemukan brand/resource spesifik. Fokus pada brand credibility dan unique value proposition.",
    }.get(search_intent or "informational", "")

    kd_guide = ""
    if keyword_difficulty is not None:
        if keyword_difficulty >= 70:
            kd_guide = f"Keyword difficulty {keyword_difficulty}/100 (HARD): artikel harus sangat komprehensif, lebih mendalam dari kompetitor, sertakan data/statistik, expert insight."
        elif keyword_difficulty >= 40:
            kd_guide = f"Keyword difficulty {keyword_difficulty}/100 (MEDIUM): artikel solid dan lengkap, pastikan semua subtopik penting tercakup."
        else:
            kd_guide = f"Keyword difficulty {keyword_difficulty}/100 (EASY): fokus pada kualitas dan kegunaan, pastikan E-E-A-T terpenuhi."

    serp_guide = ""
    if serp_features:
        hints = []
        if "featured_snippet" in serp_features:
            hints.append("tambah definition box atau tabel ringkasan di awal untuk optimasi Featured Snippet")
        if "paa" in serp_features:
            hints.append("sertakan FAQ section (H2 'Pertanyaan Umum') untuk optimasi People Also Ask")
        if "local_pack" in serp_features:
            hints.append("sertakan informasi lokal yang relevan untuk optimasi Local Pack")
        if "image_pack" in serp_features:
            hints.append("tambah deskripsi/caption gambar yang informatif untuk optimasi Image Pack")
        if hints:
            serp_guide = "SERP features target: " + "; ".join(hints) + "."

    system_msg = (
        f"Kamu adalah SEO content writer profesional Bahasa Indonesia, expert dalam E-E-A-T dan on-page SEO. "
        f"Buat artikel blog SEO berkualitas tinggi, tone: '{tone}', target sekitar {word_count} kata. "
        f"{intent_guide} {kd_guide} {serp_guide} "
        f"Gunakan heading H2/H3 dengan format markdown (## dan ###). "
        f"Optimalkan keyword secara natural (density 1-2%, jangan keyword stuffing). "
        f"Struktur artikel: hook intro, isi dengan heading logis, kesimpulan + CTA. "
        f"WAJIB output dengan format TEPAT berikut (jangan tambah teks lain di luar format):\n"
        f"TITLE: <judul artikel>\n"
        f"META: <meta description max 160 karakter, include keyword>\n"
        f"FOCUS_KEYWORD: <keyword utama>\n"
        f"SECONDARY_KEYWORDS: <keyword1>, <keyword2>, <keyword3>\n"
        f"---ARTICLE---\n"
        f"<artikel lengkap dalam markdown>\n"
        f"---END---"
    )

    user_parts = [f"Keyword utama: {keyword}", f"Judul: {target_title}"]
    if search_intent:
        user_parts.append(f"Search intent: {search_intent}")
    if search_volume:
        user_parts.append(f"Search volume: {search_volume:,}/bulan")
    if keyword_difficulty is not None:
        user_parts.append(f"Keyword difficulty: {keyword_difficulty}/100")
    if lsi_keywords:
        user_parts.append(f"LSI/related keywords (sisipkan secara natural): {', '.join(lsi_keywords)}")
    if target_audience:
        user_parts.append(f"Target pembaca: {target_audience}")
    if target_location:
        user_parts.append(f"Target lokasi: {target_location}")
    if brand_name:
        user_parts.append(f"Brand/bisnis: {brand_name}")
    if unique_angle:
        user_parts.append(f"Angle unik artikel ini: {unique_angle}")
    if faq_topics:
        user_parts.append(f"FAQ topics yang wajib dijawab: {'; '.join(faq_topics)}")
    if internal_link_targets:
        user_parts.append(f"Halaman internal untuk disarankan sebagai internal link: {internal_link_targets}")
    user_msg = "\n".join(user_parts)
    ctx = _get_session_ctx(session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    import httpx as _httpx
    gen = ContentGeneration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        tool_type="seo_article",
        input_data=json.dumps({
            "keyword": keyword, "title": target_title, "word_count": word_count,
            "tone": tone, "search_intent": search_intent,
            "keyword_difficulty": keyword_difficulty,
        }),
        model_used=ai.get("model", ""),
        provider_name="System AI",
        status="pending",
    )
    db.add(gen)
    db.commit()

    try:
        text = _call_caption(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["openai_key"],
            base_url=ai.get("base_url", ""),
            model=ai.get("model", "gpt-4o-mini"),
            max_tokens=4000,
        )
        result = parse_seo_article_response(text, keyword)
        gen.output_data = json.dumps(result)
        gen.status = "done"
        db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}
    except Exception as e:
        gen.status = "error"
        gen.error_msg = str(e)
        db.commit()
        raise ValueError(f"Gagal generate artikel: {e}")


# ─── Content Provider CRUD ────────────────────────────────────────────────────

def list_content_providers(db: Session, tool_type: Optional[str] = None) -> list[ContentProvider]:
    q = db.query(ContentProvider)
    if tool_type:
        q = q.filter(ContentProvider.tool_type == tool_type)
    return q.order_by(ContentProvider.created_at.desc()).all()


def create_content_provider(
    db: Session,
    name: str,
    tool_type: str,
    base_url: str,
    api_key: str,
    model: str,
    extra_params: Optional[dict],
    is_active: bool,
) -> ContentProvider:
    p = ContentProvider(
        id=str(uuid.uuid4()),
        name=name,
        tool_type=tool_type,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        extra_params=json.dumps(extra_params) if extra_params else None,
        is_active=is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_content_provider(db: Session, provider_id: str, updates: dict) -> ContentProvider:
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise ValueError("Provider tidak ditemukan")
    for key in ("name", "tool_type", "base_url", "model", "is_active"):
        if key in updates:
            val = updates[key]
            if key == "base_url" and val:
                val = val.rstrip("/")
            setattr(p, key, val)
    if "api_key" in updates and updates["api_key"] and not updates["api_key"].endswith("***"):
        p.api_key = updates["api_key"]
    if "extra_params" in updates:
        p.extra_params = json.dumps(updates["extra_params"]) if updates["extra_params"] else None
    db.commit()
    db.refresh(p)
    return p


def delete_content_provider(db: Session, provider_id: str) -> None:
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise ValueError("Provider tidak ditemukan")
    db.delete(p)
    db.commit()