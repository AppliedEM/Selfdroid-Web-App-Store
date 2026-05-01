# Integration Testing Buildout — Synopsis

## Overview

Created 176 unit, integration, and end-to-end tests covering all user upload, pricing, admin approval, and XMR payment features. Tests are organized in `src/tests/` with `unit/`, `integration/`, and `e2e/` directories. All 176 tests pass.

## Test Infrastructure

### Files

| File | Purpose |
|------|---------|
| `src/tests/conftest.py` | Shared fixtures: `app`, `client`, `db_session`, `admin_user_account`, `test_user_account`, `logged_in_client`, `logged_in_admin_client`, `test_app_metadata` |
| `src/tests/pytest.ini` | pytest config: test paths, markers (`integration`, `e2e`) |
| `src/tests/requirements.txt` | Test deps: pytest, pytest-cov, Flask, Flask-SQLAlchemy, Flask-WTF, Flask-Talisman, bcrypt, qrcode, WTForms, Werkzeug, SQLAlchemy |
| `src/tests/unit/__init__.py` | Package marker |
| `src/tests/integration/__init__.py` | Package marker |
| `src/tests/e2e/__init__.py` | Package marker |

### Running Tests

```bash
# All tests
cd src && python3 -m pytest tests/ -v --tb=short

# Unit tests only (no server required)
cd src && python3 -m pytest tests/unit/ -v --tb=short

# Integration tests (Flask test client, no server required)
cd src && python3 -m pytest tests/integration/ -v --tb=short

# E2E tests (Flask test client)
cd src && python3 -m pytest tests/e2e/ -v --tb=short

# Coverage
cd src && python3 -m pytest tests/ --cov=selfdroid --cov-report=html --cov-report=term-missing
```

## Test Coverage

### Unit Tests (101 tests)

| File | Tests | Coverage |
|------|-------|----------|
| `unit/test_models.py` | 20 | `UserAccountDBModel` columns/constraints, `AppSaleDBModel` columns/defaults/methods, `AppMetadataDBModel` new columns |
| `unit/test_crud.py` | 26 | `UserAccountManager` (create/auth/deactivate/reset/delete/change_password), `AppSaleManager` (create/confirm/expire/lookup) |
| `unit/test_app_metadata.py` | 8 | `AppMetadata.is_free` property, `to_api_dict()` field inclusion |
| `unit/test_authenticator.py` | 11 | `WebAuthenticator.log_in_as_user_account()`, `log_out()`, privilege checks, session expiry |
| `unit/test_web_helpers.py` | 5 | `WebHelpers.generate_web_template_context()` includes user account vars |
| `unit/test_settings.py` | 13 | Settings defaults and env var overrides for upload/pricing/expiration |
| `unit/test_invoice.py` | 12 | `PaymentInvoice` columns, defaults, `is_expired()`, `to_dict()` |

### Integration Tests (61 tests)

| File | Tests | Coverage |
|------|-------|----------|
| `integration/test_web_endpoints.py` | 61 | All web endpoints: account management, login, upload, approval, payment, download |

#### UserAdminCreateAccountEndpoint (4 tests)

- GET requires admin
- POST creates account
- POST rejects duplicate username
- POST shows form errors for invalid input

#### UserAdminManageAccountsEndpoint (6 tests)

- GET requires admin
- GET lists accounts
- Deactivate/activate actions
- Reset password action
- Delete action

#### UserLoginEndpoint (6 tests)

- GET shows form
- POST valid login (session + redirect)
- POST invalid password
- POST nonexistent user
- POST deactivated user
- POST empty form fields

#### AdminPendingSubmissionsEndpoint (3 tests)

- GET requires admin
- GET shows pending apps
- GET empty list

#### AdminApproveAppEndpoint (6 tests)

- POST requires admin
- POST approves app (is_approved, is_published)
- POST sets approved_by/approved_at
- POST nonexistent app → 404
- POST redirects to pending

#### AdminRejectAppEndpoint (7 tests)

- POST requires admin
- POST rejects app
- POST sets rejection_reason
- POST optional reason
- POST nonexistent app → 404
- POST redirects to pending

#### PaymentCreateInvoiceEndpoint (5 tests)

- GET requires user
- GET free app redirects
- GET creates sale + subaddress
- GET nonexistent app → 404
- POST creates invoice

#### PaymentCheckStatusEndpoint (3 tests)

- GET nonexistent sale → error
- GET pending sale → status=pending
- GET confirmed sale → status=confirmed

#### PaymentDownloadEndpoint (2 tests)

- GET no confirmed sale → redirect
- GET confirmed sale → serves APK

#### PaymentQREndpoint (3 tests)

- GET returns PNG with correct mimetype
- GET nonexistent sale → 404
- GET QR contains monero URI

#### UserUploadAppEndpoint (14 tests)

- GET requires user
- GET shows form
- POST valid upload (is_approved=False, is_published=False)
- POST sets uploaded_by FK
- POST sets owner_username
- POST sets price_usd
- POST sets price_xmr (via exchange rate)
- POST currency selector
- POST free app (NULL prices)
- POST duplicate package name → error
- POST invalid APK → error
- POST invalid form fields

#### WebDownloadAPKEndpoint (5 tests)

- Download free app → APK served
- Download paid app with confirmed sale → APK served
- Download paid app without confirmed sale → redirect to payment
- Download unpublished app → 404
- Download nonexistent app → 404

### E2E Tests (14 tests)

| Test | Flow |
|------|------|
| `e2e_admin_creates_user` | Admin creates user → user authenticates |
| `e2e_user_uploads_app` | User uploads APK → admin approves → app published |
| `e2e_user_uploads_paid_app` | User uploads paid app → buyer sees price |
| `e2e_admin_rejects_app` | Admin rejects → app not published, reason stored |
| `e2e_account_deactivation` | Admin deactivates → user cannot log in |
| `e2e_password_reset_admin` | Admin resets password → user logs in with new password |
| `e2e_password_reset_self` | User changes own password → logs in with new password |
| `e2e_free_app_no_payment` | Free app downloads without payment |
| `e2e_index_shows_price` | Index displays price and owner columns |
| `e2e_app_details_shows_price` | Details page displays price, owner, payment button |
| `e2e_nav_admin_links` | Admin sees Pending and Accounts nav links |
| `e2e_nav_user_upload_button` | Logged-in user sees Upload App button |
| `e2e_download_enforcement` | Anonymous user cannot download paid app |
| `e2e_currency_conversion` | USD price → price_xmr calculated correctly |

## Source Code Fixes During Testing

Several pre-existing bugs were discovered and fixed during test development:

| Bug | File | Fix |
|-----|------|-----|
| `EndpointBase.__init__` didn't propagate `url_params` to `super()` | `EndpointBase.py` | Added MRO-aware `super().__init__()` call |
| `AdminApproveAppEndpoint` missing `EndpointWithAppIDBase` mixin | `AdminApproveAppEndpoint.py` | Added mixin class |
| `AdminRejectAppEndpoint` missing `EndpointWithAppIDBase` mixin | `AdminRejectAppEndpoint.py` | Added mixin class |
| `AppMetadataDBModel` missing `is_free` property | `AppMetadataDBModel.py` | Added `@property is_free` |
| `WebEndpointBase` missing `jsonify_and_finish_request` method | `WebEndpointBase.py` | Added method |
| Template referenced non-existent route `fl_web_admin_manage_accounts` | `admin_user_accounts.html` | Fixed to `fl_web_admin_user_accounts` |
| Template referenced `sale_id` instead of `app_id` for QR route | `payment_page.html` | Fixed param name |
| `PaymentCreateInvoiceEndpoint` had `gateway` UnboundLocalError | `PaymentCreateInvoiceEndpoint.py` | Moved `gateway = MoneroGateway()` outside conditional |
| `PaymentDownloadEndpoint` referenced wrong upload route name | `PaymentDownloadEndpoint.py` | Fixed to `fl_web_user_upload_app` |
| `UserUploadAppEndpoint` referenced wrong upload route name | `UserUploadAppEndpoint.py` | Fixed to `fl_web_user_upload_app` |
| `/admin/user-accounts` only accepted GET (missing POST) | `web/__init__.py` | Added `POST` method |
| `SESSION_COOKIE_SAMESITE` was bool instead of string in conftest | `conftest.py` | Changed `True` to `"Lax"` |

## Test Architecture

```
tests/
├── conftest.py              # Shared fixtures (session-scoped app, function-scoped db)
├── pytest.ini               # Config + markers
├── requirements.txt         # Test dependencies
├── unit/
│   ├── test_models.py       # DB model columns, defaults, constraints
│   ├── test_crud.py         # CRUD manager operations
│   ├── test_app_metadata.py # AppMetadata wrapper (is_free, to_api_dict)
│   ├── test_authenticator.py # WebAuthenticator session logic
│   ├── test_web_helpers.py  # Template context generation
│   ├── test_settings.py     # Settings defaults + env overrides
│   └── test_invoice.py      # PaymentInvoice model
├── integration/
│   └── test_web_endpoints.py # All web endpoint integration tests
└── e2e/
    └── test_e2e.py          # End-to-end flow tests
```

### Fixture Hierarchy

```
app_config (session) → app (session) → client / runner (function)
    → db_session (function) → admin_user_account / test_user_account / test_app_metadata (function)
        → logged_in_client / logged_in_admin_client (function)
```

### Key Fixture Details

- **`db_session`**: Clears all data (user accounts, app metadata, sales) before/after each test for isolation
- **`logged_in_client`**: Sets session cookies with `web_has_user_privileges=True`, `user_account_id`, `user_account_username`
- **`logged_in_admin_client`**: Same as above but with `web_has_admin_privileges=True`
- **`app_config`**: Uses `sqlite:///:memory:` for tests, `WTF_CSRF_ENABLED=False`, `TESTING=True`

## Test Results

| Category | Tests | Passed | Failed |
|----------|-------|--------|--------|
| Unit | 101 | 101 | 0 |
| Integration | 61 | 61 | 0 |
| E2E | 14 | 14 | 0 |
| **Total** | **176** | **176** | **0** |

## Pre-Deployment Checklist

1. [ ] Review test coverage gaps against `docs/user_buildout_testing.md` requirements
2. [ ] Verify all 176 tests pass in clean environment
3. [ ] Run with `--cov=selfdroid` to check coverage thresholds
4. [ ] Test with Monero testnet for payment endpoint coverage
5. [ ] Add CI/CD integration (GitHub Actions recommended)
