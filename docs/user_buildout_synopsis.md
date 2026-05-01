# User App Upload & Payment Buildout — Synopsis

## Overview

Added user account management, user-initiated app upload with pricing, admin approval workflow, and XMR payment flow to Selfdroid. Logged-in users (non-admin) can now upload APKs, set prices in USD or XMR, and buyers can pay via Monero invoices. Admins approve/reject submissions and manage user accounts.

## What Was Built

### Database Models

| File | Purpose |
|------|---------|
| `src/selfdroid/appstorage/UserAccountDBModel.py` | New `user_account` table — id, username (unique), password_hash, is_active, created_at, created_by (FK) |
| `src/selfdroid/appstorage/AppSaleDBModel.py` | New `app_sale` table — id, app_id (FK), buyer_user_id (FK), amount_usd, amount_xmr, currency, payment_status, invoice_id, download_issued_at, created_at |
| `src/selfdroid/appstorage/AppMetadataDBModel.py` | Modified — added 10 columns: uploaded_by, owner_username, price_usd, price_xmr, currency, is_published, is_approved, approved_by, approved_at, rejection_reason |
| `src/selfdroid/appstorage/AppMetadata.py` | Modified — added new field mappings, `is_free` property, updated `to_api_dict()` with pricing/ownership fields |

### CRUD Layer

| File | Purpose |
|------|---------|
| `src/selfdroid/appstorage/crud/UserAccountManager.py` | User account operations: create, authenticate, deactivate, activate, reset_password, delete, change_password_for_self |
| `src/selfdroid/appstorage/crud/AppSaleManager.py` | Sale operations: create, confirm, expire, lookup by app+user, list pending/user sales |

### Web Forms

| File | Purpose |
|------|---------|
| `src/selfdroid/web/forms/UserAccountForms.py` | `UserAdminCreateAccountForm` (username/password) + `UserAccountLoginForm` (username/password) |
| `src/selfdroid/web/forms/UserUploadAppForm.py` | `UserUploadAppForm` (APK file, USD price, currency selector USD/XMR) |

### Web Endpoints

| File | Route | Auth | Purpose |
|------|-------|------|---------|
| `src/selfdroid/web/endpoints/UserLoginEndpoint.py` | `/web/user-login` | Public | Dedicated user login via username/password |
| `src/selfdroid/web/endpoints/UserUploadAppEndpoint.py` | `/web/upload-app` | User+ | Upload APK with price/currency; creates unapproved app_metadata row |
| `src/selfdroid/web/endpoints/UserAdminCreateAccountEndpoint.py` | `/web/admin/create-account` | Admin | Create new user account |
| `src/selfdroid/web/endpoints/UserAdminManageAccountsEndpoint.py` | `/web/admin/user-accounts` | Admin | List/deactivate/activate/reset/delete user accounts |
| `src/selfdroid/web/endpoints/AdminPendingSubmissionsEndpoint.py` | `/web/admin/pending` | Admin | List apps with is_approved=False |
| `src/selfdroid/web/endpoints/AdminApproveAppEndpoint.py` | `/web/admin/approve/<id>` | Admin | Set is_approved=True, is_published=True, record approved_by/approved_at |
| `src/selfdroid/web/endpoints/AdminRejectAppEndpoint.py` | `/web/admin/reject/<id>` | Admin | Set is_approved=False, is_published=False, record rejection_reason |
| `src/selfdroid/web/endpoints/PaymentCreateInvoiceEndpoint.py` | `/web/payment/create-invoice/<id>` | User+ | Create app_sale record + XMR invoice via MoneroGateway |
| `src/selfdroid/web/endpoints/PaymentCheckStatusEndpoint.py` | `/web/payment/check-status/<id>` | User+ | JSON endpoint: poll payment status, auto-confirm on payment |
| `src/selfdroid/web/endpoints/PaymentDownloadEndpoint.py` | `/web/payment/download/<id>` | User+ | Serve APK after confirmed payment |
| `src/selfdroid/web/endpoints/PaymentQREndpoint.py` | `/web/payment/qr/<id>` | User+ | Generate PNG QR code for monero: URI |

### Templates

| File | Purpose |
|------|---------|
| `src/selfdroid/web/templates/web_user_login.html` | User login form (username/password) |
| `src/selfdroid/web/templates/web_user_upload.html` | Upload form with APK picker, price field, currency radio |
| `src/selfdroid/web/templates/admin_user_accounts.html` | Admin table of accounts with activate/deactivate/reset/delete actions |
| `src/selfdroid/web/templates/admin_pending_submissions.html` | Admin table of pending apps with approve/reject actions |
| `src/selfdroid/web/templates/payment_page.html` | Payment display: QR code, address, amounts, auto-refresh polling (10s) |

### Template Modifications

| File | Changes |
|------|---------|
| `src/selfdroid/web/templates/web_index.html` | Added "Upload App" button (user+), Price column, Owner column |
| `src/selfdroid/web/templates/web_app_details.html` | Added Price/Owner rows, payment button for paid apps, XMR price display |
| `src/selfdroid/web/templates/_web_base.html` | Added "Pending" and "Accounts" nav links for admin |

### Authenticator & Helpers

| File | Changes |
|------|---------|
| `src/selfdroid/web/authenticator/WebAuthenticator.py` | Added `log_in_as_user_account()` method; logout clears `user_account_id`/`user_account_username` |
| `src/selfdroid/web/WebHelpers.py` | Added `user_account_id` and `user_account_username` to template context |
| `src/selfdroid/Settings.py` | Added `USER_UPLOAD_ENABLED`, `USER_UPLOAD_REQUIRES_APPROVAL`, `MIN_PRICE_USD`, `MIN_PRICE_XMR`, `DOWNLOAD_EXPIRY_HOURS` settings |
| `src/selfdroid/__init__.py` | Registered `UserAccountDBModel` and `AppSaleDBModel` with SQLAlchemy |

### Download Flow Changes

| File | Changes |
|------|---------|
| `src/selfdroid/web/endpoints/WebDownloadAPKEndpoint.py` | Added payment verification: checks `is_published`, `is_free`, and confirmed `app_sale` for paid apps |

### API Changes

| File | Changes |
|------|---------|
| `src/selfdroid/appstorage/AppMetadata.py` | `to_api_dict()` now includes: `uploaded_by`, `owner_username`, `owner_user_id`, `price_usd`, `price_xmr`, `currency`, `is_published`, `is_approved`, `is_free` |

### Dependencies

| File | Changes |
|------|---------|
| `src/requirements.txt` | `qrcode[pil]` and `Pillow` already present (payment module) |

### Documentation

| File | Purpose |
|------|---------|
| `docs/future_development.md` | Future features: upload limits, revenue split, refunds, API upload, bulk accounts, analytics, etc. |

## Architecture

```
User Flow:
  User logs in (/web/user-login) → uploads APK (/web/upload-app)
    → app_metadata created with is_approved=False, is_published=False
    → Admin reviews (/web/admin/pending) → approves or rejects
    → If approved: app appears on index with price
    → Buyer visits app details → clicks download
    → If paid: creates app_sale + XMR invoice → shows QR code
    → Auto-poll checks payment status → on confirmed: serves APK

Admin Flow:
  Admin logs in → sees "Pending" and "Accounts" nav links
  /web/admin/pending → approve/reject submissions
  /web/admin/user-accounts → create/deactivate/activate/reset/delete accounts

Payment Flow:
  Buyer clicks download on paid app
    → PaymentCreateInvoiceEndpoint creates app_sale (status=pending)
    → MoneroGateway.create_invoice_address() generates unique subaddress
    → payment_page.html shows QR code + address, polls /payment/check-status every 10s
    → PaymentCheckStatusEndpoint calls MoneroGateway.check_payment()
    → On confirmed: AppSaleManager.confirm_sale() → redirect to /payment/download
    → PaymentDownloadEndpoint serves APK
```

## Key Design Decisions

- **No intermediate UploadedApp model**: Submissions go directly to `app_metadata` with `is_approved=False`, per user's decision.
- **Denormalized owner_username**: Stored as string on `app_metadata` for display; admin can reassign. FK to `user_account.id` is on `uploaded_by`.
- **All payments in XMR**: USD prices are converted to XMR at spot rate via CoinGecko. No USD payment processor needed.
- **Auto-confirm payments**: `PaymentCheckStatusEndpoint` auto-confirms and redirects to download on payment detection (no webhook needed).
- **Account deactivation deletes apps**: Per user's request — deactivated accounts have their apps deleted.
- **User password reset**: Users can change password after login; admin can reset for any account.
- **Feature flag**: `USER_UPLOAD_ENABLED` setting controls whether users can upload (default: enabled).

## Pre-Deployment Checklist

1. [ ] Review and adjust `Settings.USER_UPLOAD_ENABLED` and other new settings
2. [ ] Set `SELFDROID_USER_UPLOAD_REQUIRES_APPROVAL` if different from default
3. [ ] Configure `SELFDROID_MIN_PRICE_USD` and `SELFDROID_MIN_PRICE_XMR` if different from defaults
4. [ ] Verify Monero wallet-rpc is running (required for payment flow)
5. [ ] Test admin account creation flow
6. [ ] Test user login with dedicated account
7. [ ] Test user APK upload with pricing
8. [ ] Test admin approve/reject workflow
9. [ ] Test payment flow (create invoice → pay → auto-confirm → download)
10. [ ] Test download enforcement on paid apps without confirmed payment

## Routes Summary

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/web/user-login` | GET/POST | Public | User login page |
| `/web/upload-app` | GET/POST | User+ | User app upload form |
| `/web/admin/user-accounts` | GET | Admin | Manage user accounts |
| `/web/admin/create-account` | POST | Admin | Create user account |
| `/web/admin/pending` | GET | Admin | Pending submissions |
| `/web/admin/approve/<id>` | POST | Admin | Approve submission |
| `/web/admin/reject/<id>` | POST | Admin | Reject submission |
| `/web/payment/create-invoice/<id>` | GET/POST | User+ | Create XMR payment |
| `/web/payment/check-status/<id>` | GET | User+ | JSON payment status |
| `/web/payment/download/<id>` | GET | User+ | Download after payment |
| `/web/payment/qr/<id>` | GET | User+ | QR code image |

## Estimated Effort (Remaining)

| Task | Effort |
|------|--------|
| Template polish (styling, edge cases) | 2 hours |
| Payment flow testing (testnet) | 2 hours |
| Admin account management testing | 1 hour |
| Upload flow testing | 1 hour |
| Approval workflow testing | 1 hour |
| Download enforcement testing | 1 hour |
| **Total remaining** | **~7 hours** |
