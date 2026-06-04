# Backend Refactor Plan — June 4, 2026

## Kondisi Saat Ini

- `main.py`: **9,475 baris**, 386+ fungsi
- 13 file router di `routers/`, masing-masing import 14 symbol dari `main.py`
- Semua endpoint ADA di kedua tempat (main.py dan router) — double registration
- Scheduler diduplikasi di `main.py` dan `routers/workspace.py`
- **22 broken import** di 10 router file (NameError saat runtime)
- Banyak helper function diduplikasi antara main.py dan routers

## Goals

1. `main.py` jadi ramping (~200 baris): app setup, middleware, config, router includes, scheduler
2. Semua endpoint cuma ada di router file masing-masing
3. Shared utilities dipindah ke `app/core/dependencies.py`
4. Scheduler cuma satu (di main.py)
5. Semua broken import terfix

---

## Phase 1: Buat `app/core/dependencies.py` (shared utilities)

File baru yang berisi semua fungsi yg diimport routers dari main.py:

`backend/app/core/dependencies.py`:
- Auth: `hash_password`, `verify_password`, `create_token`, `get_current_user`, `require_admin`
- Rate limit: `_check_login_rate_limit`, `_record_login_failure`, `_record_login_success`, `_check_simple_rate_limit`, `search_semaphore`
- Encryption: `encrypt_password`, `decrypt_password`, `_fernet`
- Config: `SECRET_ENCRYPTION_KEY`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_HOURS`, `FRONTEND_URL`, `GOOGLE_API_KEY`, `FONNTE_WEBHOOK_SECRET`, `UPLOADS_DIR`, `ADMIN_WA`
- DB: `SessionLocal` (import from models)
- Fonnte: `get_fonnte_token`, `send_fonnte_message`, `_send_fonnte_sync`
- Settings: `_get_setting`, `SENSITIVE_SETTING_KEYS`, `_mask_secret`
- AI: `get_ai_config`, `build_analysis_prompt`, `_call_ai_sync`, `call_ai_provider`, `parse_ai_response`
- 9router: `get_9router_config`, `get_proxy_for_feature`, all combo helpers
- Leads: `normalize_phone`, `_normalize_phone`, `make_wa_url`, `calculate_lead_score`, `calculate_lead_score_full`, `_apply_proposal_signal`, `generate_batch_name`
- Report: `generate_report_for_lead`
- Cost: `log_outreach_cost`, `log_ai_cost`
- Proposals: `_build_addons_from_products`, `_build_roi_data`, `generate_unique_slug`, `slugify`
- Google: `_get_google_calendar_service`, `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`
- Hermes: `HERMES_GATEWAY_URL`, `_hermes_headers`, `_office_profile`
- Model helpers: `_ai_model_to_out`, `_ads_out`
- Board sync: `sync_row_to_board`, `sync_row_status_to_board`
- Workspace: `WORKSPACE_TEMPLATES`, `build_sheets_for_service`, `build_sheets_for_days` from workspace_templates
- Various: `_detect_project_type`, `_detect_service_type`, `_detect_contract_months`, `seed_data`

## Phase 2: Bersihin `routers/workspace.py`

- Hapus seluruh scheduler block (line 1289-1533)
- Hapus content generator schemas duplikat (line 1535-1739)
- Fix imports: ganti `from main import ...` jadi `from app.core.dependencies import ...`

## Phase 3: Fix imports di semua router

Ganti import line di semua 13 router:
```python
from main import get_current_user, require_admin, ...
```
Jadi:
```python
from app.core.dependencies import get_current_user, require_admin, ...
```

Dan tambahkan imports yg sebelumnya broken (NameError).

## Phase 4: Sterilkan `main.py`

Hapus semua endpoint function (128+ fungsi) dan helper duplikat dari main.py.
Yang tersisa di main.py:
- Imports
- App creation + CORS
- Middleware
- Static files
- Scheduler (SATU copy)
- Router includes

## Phase 5: Verifikasi

- Test import: `python -c "from main import app"`
- Cek tidak ada dual route: pastikan tiap path cuma muncul 1x
- Run test: `cd backend && python -m pytest tests/ -v`
