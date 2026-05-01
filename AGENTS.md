# Selfdroid — Agent Instructions

## Project Overview

Selfdroid is a self-hosted Android app store (Flask + SQLite). Users upload APKs, admin manages apps. Monero (XMR) payments are supported via `monero-wallet-rpc`.

**Monorepo layout:**
- `src/selfdroid/` — Flask app code
- `src/selfdroid/web/` — Web UI (templates, endpoints, forms)
- `src/selfdroid/api/v1/` — Public JSON API
- `src/selfdroid/payments/` — Monero payment module
- `src/selfdroid/appstorage/` — App metadata model, APK parsing, CRUD
- `docs/` — Buildout plans and synopsis
- `wallet_data/` — Monero view-only wallet (gitignored)
- `app_data/` — SQLite DB, APKs, icons (gitignored)

## Setup & Running

```bash
cd src
./prepare.sh          # Creates venv + self-signed certs (idempotent)
./run_dev_server.sh   # Starts Flask dev server on HTTPS
```

Production: Docker (`docker-compose.yml`) or uWSGI + nginx. See `docs/README.md`.

## Architecture Notes

- **DB**: SQLite, auto-created via `db.create_all()` on startup. **No migrations tool** — schema changes require manual DB manipulation.
- **Auth**: Shared password-based (user/admin). Dedicated user accounts stored in `user_account` table. Password hashes in `Settings.py` or env vars (`SELFDROID_USER_PASSWORD_HASH`, `SELFDROID_ADMIN_PASSWORD_HASH`).
- **App storage**: `app_data/apks/` and `app_data/icons/` — files keyed by app ID. `AppStorageHelpers` generates paths.
- **APK parsing**: Uses `pyaxmlparser` to extract metadata + icon from uploaded APK.
- **Payment**: `monero-wallet-rpc` (Docker) required for XMR payments. CoinGecko API for XMR/USD conversion. Background `PaymentChecker` thread polls every 30s.
- **Endpoint pattern**: Each route has its own endpoint class with `handle_request()`, executed via `EndpointExecutor`. Base classes enforce auth: `WebAtLeastUserEndpointBase`, `WebAdminEndpointBase`.
- **CSP**: Flask-Talisman enforces strict Content-Security-Policy with nonces. Templates use `nonce="{{ csp_nonce() }}"` on scripts/styles.

## Gotchas

- **No test infrastructure** — no pytest, no linting, no type checking. If you add tests, create `src/tests/` and document how to run them.
- **No lockfile** — `requirements.txt` has pinned versions but no `pip freeze` output.
- **`prepare.sh` creates `src/virtualenv/` and `src/self_signed_certs/`** — don't assume they exist; run `prepare.sh` first.
- **`app_data/` is gitignored** — DB and uploaded files live here. Never commit it.
- **Monero wallet-rpc is required for payment endpoints** — if wallet-rpc is down, payment creation fails.
- **`Settings.py` has hardcoded dev passwords** — override via env vars in production.
- **Flask-SQLAlchemy 2.5.1** — uses `Model.query` style, not `db.session.execute(select(...))`.
- **`db.create_all()` on every startup** — safe for SQLite, but won't alter existing tables.

## Key Entry Points

- App factory: `src/selfdroid/__init__.py` — creates Flask app, registers blueprints, initializes DB
- Entry: `src/selfdroid/selfdroid.py` — imports `app` from `selfdroid`
- Web routes: `src/selfdroid/web/__init__.py` — all `/web/*` routes
- API routes: `src/selfdroid/api/v1/__init__.py` — all `/api/v1/*` routes
- Payment routes: `src/selfdroid/payments/endpoints.py` — all `/web/payment-*` routes

## Relevant Docs

- `docs/README.md` — deployment & usage guide
- `docs/user_buildout.md` — user app upload & payment implementation plan
- `docs/user_buildout_synopsis.md` — synopsis of user buildout changes
- `docs/user_buildout_testing.md` — recommended tests
- `docs/monero_payments_buildout.md` — payment module buildout plan
- `docs/buildout_synopsis.md` — payment module synopsis
- `docs/future_development.md` — planned features

## Web Endpoints (`/web/*`)

Blueprint: `web_blueprint` (`url_prefix="/web"`). Each route has its own endpoint class with `handle_request()`.

| URL | Method | Auth | Class | Description |
|-----|--------|------|-------|-------------|
| `/web/login` | GET, POST | Public (redirects if logged in) | `WebLoginEndpoint` | Admin/user password login. Two modes: admin or user. If user password hash is None (dev mode), login is passwordless. |
| `/web/logout` | POST | At least user | `WebLogoutEndpoint` | Clears session cookies. Redirects to login. |
| `/web/` | GET | At least user | `WebIndexEndpoint` | Main app listing page. If admin, also renders add-app form. |
| `/web/app-details/<int:app_id>` | GET | At least user | `WebAppDetailsEndpoint` | Single app detail page. If admin, also renders update/delete forms. |
| `/web/app-icon/<int:app_id>` | GET | At least user | `WebAppIconEndpoint` | Serves app icon PNG from `Constants.ICONS_DIRECTORY`. |
| `/web/download-apk/<int:app_id>` | GET | At least user | `WebDownloadAPKEndpoint` | Downloads APK. Checks: app published, buyer has confirmed sale OR redirects to payment. Free apps bypass payment. |
| `/web/add-app` | POST | Admin only | `WebAddAppEndpoint` | Admin uploads APK. Parses metadata via `APKParser`, creates DB row, saves APK + icon to disk. |
| `/web/update-app/<int:app_id>` | POST | Admin only | `WebUpdateAppEndpoint` | Admin updates app with new APK. Validates package_name matches, version_code > current. Replaces APK + icon. |
| `/web/delete-app/<int:app_id>` | POST | Admin only | `WebDeleteAppEndpoint` | Admin deletes app. Removes DB row, APK file, icon file. |
| `/web/user-login` | GET, POST | Public (redirects if logged in) | `UserLoginEndpoint` | Registered user account login (username + bcrypt). Sets `user_account_id` + `user_account_username` in session. |
| `/web/upload-app` | GET, POST | At least user | `UserUploadAppEndpoint` | User submits APK for admin approval. Creates DB row with `is_published=False`, `is_approved=False`. |
| `/web/admin/user-accounts` | GET | Admin only | `UserAdminManageAccountsEndpoint` | Lists all user accounts. Actions: deactivate, activate, reset_password, delete. |
| `/web/admin/create-account` | POST | Admin only | `UserAdminCreateAccountEndpoint` | Admin creates new user account via `UserAccountManager.create_account()`. |
| `/web/admin/pending` | GET | Admin only | `AdminPendingSubmissionsEndpoint` | Lists all apps where `is_approved=False`, ordered by `added_datetime` desc. |
| `/web/admin/approve/<int:app_id>` | POST | Admin only | `AdminApproveAppEndpoint` | Sets `is_approved=True`, `is_published=True`, records `approved_by` + `approved_at`. |
| `/web/admin/reject/<int:app_id>` | POST | Admin only | `AdminRejectAppEndpoint` | Sets `is_approved=False`, `is_published=False`, stores `rejection_reason`. |
| `/web/payment/create-invoice/<int:app_id>` | GET, POST | At least user | `PaymentCreateInvoiceEndpoint` | Creates Monero payment invoice for a paid app. Generates subaddress via `gateway.create_invoice_address()`. |
| `/web/payment/check-status/<int:sale_id>` | GET | At least user | `PaymentCheckStatusEndpoint` | Checks payment status via `gateway.check_payment()`. Auto-confirms if payment received. Returns JSON. |
| `/web/payment/download/<int:sale_id>` | GET | At least user | `PaymentDownloadEndpoint` | Serves APK if sale `payment_status` is "confirmed". Otherwise redirects with error. |
| `/web/payment/qr/<int:sale_id>` | GET | At least user | `PaymentQREndpoint` | Generates and serves PNG QR code for Monero payment URI. |

## API Endpoints (`/api/v1/*`)

Blueprint chain: `api_blueprint` (`/api`) → `api_v1_blueprint` (`/api/v1`). API auth via header `X-SelfdroidAPI-Password` (base64-encoded user password). Admin access is explicitly forbidden via API.

| URL | Method | Auth | Description |
|-----|--------|------|-------------|
| `/api/` | GET | None | Version discovery. Returns `{"is_selfdroid_api": true, "supported_api_versions": [1]}`. |
| `/api/v1/info` | GET | User password | Returns instance info: version, instance name, supported API versions. |
| `/api/v1/app-details` | GET | User password | JSON array of ALL app metadata (via `to_api_dict()`). Uses app storage lock. |
| `/api/v1/app-details/<int:app_id>` | GET | User password | JSON object for a single app's metadata. Uses app storage lock. |
| `/api/v1/app-icon/<int:app_id>` | GET | User password | Serves app icon PNG as attachment `{app_name}.png`. Uses app storage lock. |
| `/api/v1/download-apk/<int:app_id>` | GET | User password | Serves APK file as attachment `{app_name}.apk`. Uses app storage lock. |

## Payment Endpoints (from `payments/endpoints.py`)

Blueprint: `web_payments_blueprint` (registered via `init_payments(app)`).

| URL | Method | Auth | Description |
|-----|--------|------|-------------|
| `/web/payment-checkout` | GET, POST | Admin only | Creates payment invoice. POST: generates Monero subaddress, converts fiat→XMR, generates QR code, renders invoice page. |
| `/web/payment-status/<int:invoice_id>` | GET | None | Returns JSON with invoice dict + payment check result from gateway. |
| `/web/payment-qr/<int:invoice_id>` | GET | None | Returns PNG QR code image for a payment invoice's Monero URI. |
| `/web/payment-webhook` | POST | None | External webhook receiver. Updates invoice status, confirmations, payment_tx_hash from JSON body. |

Background: `PaymentChecker` singleton polls every 30s for pending/expiring invoices. Auto-updates status to "confirming" or "confirmed".

## Database Models

### `app_metadata` — `AppMetadataDBModel`
File: `src/selfdroid/appstorage/AppMetadataDBModel.py`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | App ID (non-reusable) |
| `app_name` | String(256) | NOT NULL | Display name |
| `package_name` | String(512) | UNIQUE, NOT NULL | Android package name (e.g., `com.example.app`) |
| `version_code` | Integer | NOT NULL | Internal version code |
| `version_name` | String(32) | NOT NULL | Human-readable version (e.g., `1.0.0`) |
| `min_api_level` | Integer | NOT NULL | Minimum Android API level |
| `max_api_level` | Integer | nullable | Maximum Android API level |
| `apk_file_size` | Integer | NOT NULL | APK size in bytes |
| `uploaded_by` | Integer | FK → `user_account.id` | User who uploaded |
| `owner_username` | String(128) | nullable | App owner username |
| `price_usd` | Numeric(10,2) | nullable | Price in USD |
| `price_xmr` | Numeric(20,12) | nullable | Price in XMR |
| `currency` | String(3) | default="usd" | Currency code |
| `is_published` | Boolean | default=False | Publicly available |
| `is_approved` | Boolean | default=False | Admin approved |
| `approved_by` | Integer | FK → `user_account.id` | Admin who approved |
| `approved_at` | DateTime | nullable | Approval timestamp |
| `rejection_reason` | String(512) | nullable | Rejection reason |
| `added_datetime` | DateTime | default=utcnow | Added timestamp |
| `last_updated_datetime` | DateTime | default=utcnow, onupdate | Last modification |

### `app_sale` — `AppSaleDBModel`
File: `src/selfdroid/appstorage/AppSaleDBModel.py`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | Sale ID |
| `app_id` | Integer | FK → `app_metadata.id`, NOT NULL | Purchased app |
| `buyer_user_id` | Integer | FK → `user_account.id`, NOT NULL | Purchasing user |
| `amount_usd` | Numeric(10,2) | NOT NULL | Amount in USD |
| `amount_xmr` | Numeric(20,12) | NOT NULL | Amount in XMR |
| `currency` | String(3) | default="usd" | Currency code |
| `payment_status` | String(16) | default="pending" | pending/confirmed/expired |
| `invoice_id` | String(64) | nullable | Monero subaddress used |
| `download_issued_at` | DateTime | nullable | Download link issued time |
| `created_at` | DateTime | default=utcnow | Creation timestamp |

Methods: `is_expired()` (24h since `download_issued_at`), `to_dict()` (serializable dict).

### `user_account` — `UserAccountDBModel`
File: `src/selfdroid/appstorage/UserAccountDBModel.py`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | User ID |
| `username` | String(128) | UNIQUE, NOT NULL | Username |
| `password_hash` | String(256) | NOT NULL | bcrypt hash |
| `is_active` | Boolean | default=True | Account active |
| `created_at` | DateTime | default=utcnow | Creation timestamp |
| `created_by` | Integer | FK → `user_account.id`, NOT NULL | Admin who created |

### `payment_invoice` — `PaymentInvoice`
File: `src/selfdroid/payments/invoice.py`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, autoincrement | Invoice ID |
| `order_id` | String(64) | UNIQUE, NOT NULL | Order identifier |
| `subaddress` | String(95) | UNIQUE, NOT NULL | Monero subaddress for payment |
| `subaddress_index` | Integer | NOT NULL | Subaddress index |
| `amount_xmr` | String(32) | NOT NULL | Amount in XMR |
| `amount_fiat` | String(32) | NOT NULL | Original fiat amount |
| `fiat_currency` | String(3) | default="usd" | Fiat currency |
| `exchange_rate_at_creation` | String(32) | NOT NULL | XMR/fiat rate at creation |
| `status` | String(16) | default="pending" | pending/confirming/confirmed/expired |
| `confirmations` | Integer | default=0 | Current confirmation count |
| `required_confirmations` | Integer | default=2 | Confirmation threshold |
| `payment_tx_hash` | String(64) | nullable | Transaction hash |
| `created_at` | DateTime | default=utcnow | Creation timestamp |
| `updated_at` | DateTime | default=utcnow, onupdate | Last update |
| `expires_at` | DateTime | NOT NULL | Expiration timestamp |

Methods: `is_expired()`, `to_dict()`.

## Critical Data Paths

All paths defined in `src/selfdroid/Constants.py` and `AppStorageHelpers`.

| Constant | Value | Description |
|----------|-------|-------------|
| `DATA_DIRECTORY` | `../app_data/` (relative to `selfdroid/`) | Root data directory |
| `DATABASE_URI` | `sqlite:///app_data/database.sqlite` | SQLite database |
| `TEMPORARY_DIRECTORY` | `app_data/temp/` | Temporary APK upload |
| `APKS_DIRECTORY` | `app_data/apks/` | APK file storage |
| `ICONS_DIRECTORY` | `app_data/icons/` | Icon file storage |
| `SECRET_KEY_FILE` | `app_data/secret_key` | Flask secret key |
| `APP_STORAGE_LOCK_FILE` | `app_data/app_storage.lock` | File-based lock for concurrent access |

### File Naming Convention (by app ID)

| Resource | Filename | Full path pattern |
|----------|----------|-------------------|
| APK | `{app_id}.apk` | `{APKS_DIRECTORY}/{app_id}.apk` |
| Icon | `{app_id}.png` | `{ICONS_DIRECTORY}/{app_id}.png` |
| Temp APK | `{32-char-random}.apk` | `{TEMPORARY_DIRECTORY}/{random}.apk` |

### AppStorageHelpers Key Methods (`src/selfdroid/appstorage/AppStorageHelpers.py`)

| Method | Returns |
|--------|---------|
| `get_app_storage_lock()` | `FlockBasedLock` for `APP_STORAGE_LOCK_FILE` |
| `get_apk_path_by_app_id(app_id)` | Full APK path |
| `get_apk_filename_by_app_id(app_id)` | `{app_id}.apk` |
| `get_icon_path_by_app_id(app_id)` | Full icon path |
| `get_icon_filename_by_app_id(app_id)` | `{app_id}.png` |
| `generate_temp_filepath_for_apk_while_locked()` | Unique temp path with 32-char random string |

All CRUD operations that access both DB and filesystem are wrapped in `with AppStorageHelpers.get_app_storage_lock():` for atomicity.

## Auth Hierarchy

| Base Class | Requirement | Check |
|------------|-------------|-------|
| `WebPublicOnlyEndpointBase` | No auth; redirects to index if already logged in | `has_at_least_user_privileges()` |
| `WebAtLeastUserEndpointBase` | Must be logged in as user or admin | `has_at_least_user_privileges()` |
| `WebAdminEndpointBase` | Must be logged in as admin | `has_admin_privileges()` (implies user) |

### Session Keys (WebAuthenticator)

| Key | Purpose |
|-----|---------|
| `web_has_user_privileges` | User is logged in |
| `web_has_admin_privileges` | User has admin privileges |
| `web_login_timestamp` | Login time (for session expiry) |
| `user_account_id` | Registered user account ID |
| `user_account_username` | Registered user username |

Session expiry: `WEB_LOGIN_LIFETIME` = 10800s (3 hours). `MINIMUM_WEB_LOGIN_TIMESTAMP` = `2021-07-22 12:00:00` (invalidates old sessions on password change).

## CRUD Managers

| Manager | File | Key Methods |
|---------|------|-------------|
| `AppAdder` | `crud/AppAdder.py` | `add_app_while_locked()` — validates no duplicate package_name, creates DB row, saves APK + icon |
| `AppGetter` | `crud/AppGetter.py` | `get_all_db_models_while_locked()`, `get_db_model_while_locked()`, `get_db_model_or_404_while_locked()`, `does_app_exist_in_database()` |
| `AppUpdater` | `crud/AppUpdater.py` | `update_app_while_locked()` — validates package_name matches, version_code > current, replaces APK + icon, returns (old_meta, new_meta) |
| `AppDeleter` | `crud/AppDeleter.py` | `delete_app_while_locked()` — deletes DB row, APK file, icon file |
| `AppSaleManager` | `crud/AppSaleManager.py` | `create_sale()`, `get_by_id()`, `get_by_app_and_user()`, `confirm_sale()`, `expire_sale()`, `get_pending_sales()`, `get_sales_for_user()` |
| `UserAccountManager` | `crud/UserAccountManager.py` | `create_account()`, `authenticate()`, `get_by_id()`, `get_by_username()`, `get_all_accounts()`, `deactivate_account()`, `reset_password()`, `delete_account()`, `change_password_for_self()` |

## Key Configuration (`Settings.py`)

| Setting | Default | Env Override | Description |
|---------|---------|-------------|-------------|
| `INSTANCE_NAME` | `"Selfdroid Dev"` | — | Display name in web app title |
| `MAX_UPLOAD_SIZE` | 64 MiB | — | Flask `MAX_CONTENT_LENGTH` |
| `USER_UPLOAD_ENABLED` | `true` | `SELFDROID_USER_UPLOAD_ENABLED` | Enable user APK uploads |
| `USER_UPLOAD_REQUIRES_APPROVAL` | `true` | `SELFDROID_USER_UPLOAD_REQUIRES_APPROVAL` | Require admin approval |
| `DOWNLOAD_EXPIRY_HOURS` | 24 | — | Download link validity |
| `MIN_PRICE_USD` | `0.01` | — | Minimum app price in USD |
| `MIN_PRICE_XMR` | `0.001` | — | Minimum app price in XMR |

## APK Parsing

File: `src/selfdroid/appstorage/apk/APKParser.py`

Uses `pyaxmlparser` to extract: `app_name`, `package_name`, `version_code`, `version_name`, `min_api_level`, `max_api_level`, `apk_file_size`, `app_icon`. Icon is converted to uniform 192×192 PNG via PIL.

Validates package name against: `^[A-Za-z_][0-9A-Za-z._]+[0-9A-Za-z_]$`

`ParsedAPK` class provides `create_new_db_model_with_metadata()` and `fill_existing_db_model_with_metadata()`.

## Payment Gateway (`src/selfdroid/payments/gateway.py`)

`MoneroGateway` singleton (`gateway`). RPC URL: `http://localhost:18088/json_rpc`. Account index: `0`.

Methods: `create_invoice_address()`, `get_balance()`, `get_address_count()`, `check_payment()`, `get_xmr_usd_rate()`, `fiat_to_xmr()`, `xmr_to_fiat()`, `generate_payment_uri()`.

Exchange rates cached for 60s from CoinGecko API. Supported fiat: USD, EUR, GBP.
