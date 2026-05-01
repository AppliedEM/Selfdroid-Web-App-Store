# User App Upload & Payment - Implementation Plan

## Overview

This document outlines the high-level changes needed to allow logged-in users (non-admin) to upload APKs with custom pricing (USD or XMR), and to handle the resulting payment flow.

---

## 1. Database / Schema Changes

### 1.1 `AppMetadataDBModel` columns (new/modified)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `uploaded_by` | Integer | Yes | NULL | FK → user_account.id (user who uploaded) |
| `owner_username` | String(128) | Yes | NULL | The user who set the price (may differ from uploader if admin reassigns) |
| `price_usd` | Numeric(10,2) | Yes | NULL | Price in USD (NULL = free) |
| `price_xmr` | Numeric(20,12) | Yes | NULL | Price in XMR (NULL = free in XMR) |
| `currency` | String(3) | Yes | "usd" | Default currency: "usd" or "xmr" |
| `is_published` | Boolean | Yes | False | Whether the app is visible to users (approval gate) |
| `is_approved` | Boolean | Yes | False | Admin approval flag |
| `approved_by` | Integer | Yes | NULL | FK → user_account.id (admin who approved) |
| `approved_at` | DateTime | Yes | NULL | Timestamp of approval |
| `rejection_reason` | String(512) | Yes | NULL | Why admin rejected the submission |

### 1.2 New table: `user_account`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | PK | Primary key |
| `username` | String(128) | No | | Unique username |
| `password_hash` | String(256) | No | | bcrypt hash of password |
| `is_active` | Boolean | Yes | True | Whether account is enabled |
| `created_at` | DateTime | No | NOW | Account creation timestamp |
| `created_by` | Integer | No | FK → user_account.id | Admin who created this account |

### 1.3 New table: `app_sale`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | PK | Primary key |
| `app_id` | Integer | No | FK → app_metadata.id | Reference to the app |
| `buyer_user_id` | Integer | No | FK → user_account.id | User who bought the app |
| `amount_usd` | Numeric(10,2) | No | | Amount charged in USD |
| `amount_xmr` | Numeric(20,12) | No | | Amount charged in XMR |
| `currency` | String(3) | No | "usd" | Currency used |
| `payment_status` | String(16) | No | "pending" | "pending", "confirmed", "expired" |
| `invoice_id` | String(64) | Yes | NULL | Reference to payment_invoice.order_id |
| `download_issued_at` | DateTime | Yes | NULL | When download link was issued |
| `created_at` | DateTime | No | NOW | Sale record creation time |

---

## 2. User Identity Model

Users have dedicated accounts with username/password. Admin creates accounts via the web UI.

### 2.1 Current login flow (unchanged)
- User enters shared user password → gets "user" privileges
- User enters shared admin password → gets "admin" privileges

### 2.2 New: dedicated user accounts

Users log in with their own username and password (not the shared user password).

- `user_account` table stores username + bcrypt password hash
- Login page extended with a "Log in as user" section that accepts username/password from `user_account` table
- After login, session contains `user_id` in addition to existing privilege flags
- `has_at_least_user_privileges()` returns True if user has at least user-level privileges (shared password OR dedicated account login)

### 2.3 Admin account creation

Admin creates user accounts via a new admin page:

- Input fields: username, password (or auto-generate)
- Admin can also: deactivate account, reset password, delete account
- Username must be unique
- Password stored as bcrypt hash (same approach as existing admin password)

### 2.4 `uploaded_by` and `owner_username` on `AppMetadataDBModel`

- `uploaded_by` → Integer FK → `user_account.id` (the user who uploaded the APK)
- `owner_username` → String(128) (the username who set the price, for display purposes)
  - Set to uploader's username at creation time
  - Admin can reassign if needed
  - Derived from FK at read time, stored as denormalized string for display

### 2.5 `buyer_identifier` on `app_sale`

- Renamed to `buyer_user_id` → Integer FK → `user_account.id`
- Since buyers must be logged in, this is a FK rather than a free-text identifier
- If a non-logged-in user somehow initiates a sale (e.g., via API with key), use NULL + separate `api_key_id` field

### 2.6 `approved_by` on `AppMetadataDBModel`

- Renamed to `approved_by` → Integer FK → `user_account.id`
- Stores the admin user who approved the submission

### 2.7 Future: `UploadedApp` model (optional intermediate step)
Before creating the `app_metadata` row, create an `UploadedApp` record that:
- Stores the APK temporarily
- Stores the user_id (FK → user_account.id)
- Stores the desired price
- Stores the parsed APK metadata (extracted from APK before saving)
- Admin reviews and approves → then `app_metadata` is created

**Decision point:** Do we want an intermediate `UploadedApp` model, or go straight to creating `app_metadata` with `is_approved=False`?
A: Yes. We'll definitely need a model for UploadedApp. Will likely need to contain the following:
  1. id  
  2. name (string)
  3. hash (md5)
  4. path (in the filesystem)
  5. package_name (android package name)
  6. uploaded_by (user)
  7. price (USD or XMR)
  8. denomination ('USD' or 'XMR')
  9. approved_by (admin user)
  10. owned_by (user)
  11. is_published

---

## 3. Upload Flow

### 3.1 New files

| File | Purpose |
|------|---------|
| `src/selfdroid/web/forms/UserUploadAppForm.py` | Form with: APK file, price field, currency selector (USD/XMR) |
| `src/selfdroid/web/endpoints/UserUploadAppEndpoint.py` | Endpoint for user-initiated app upload |
| `src/selfdroid/web/templates/web_user_upload.html` | Upload form page |
| `src/selfdroid/appstorage/crud/AppUploader.py` | Business logic for user app upload (parses APK, validates, creates records) |

### 3.2 User upload form fields

```
- APK file: (file input, required, .apk only)
- Price: (number input, optional, min 0)
- Currency: (radio/select: USD / XMR)
- Note: "If price is empty, the app will be free."
```

### 3.3 Upload endpoint logic

1. User must have at least user privileges (not anonymous)
2. User must have a dedicated account (username + password login) or shared user password login
3. Validate form (APK file, price if set)
4. Parse APK → extract metadata (name, package, version, icon)
  * reference https://github.com/tdoly/apk_parse for package name parsing logic
5. Check for duplicate package name (same check as admin add)
6. Create `app_metadata` row with:
   - `uploaded_by` = current user's `user_account.id` (FK)
   - `owner_username` = current user's `username` (denormalized)
   - `is_published=False`, `is_approved=False`
7. Save APK and icon (same as admin flow)
8. Redirect to "submission pending" confirmation page

### 3.4 New route

```python
@web_blueprint.route("/upload-app", methods=["GET", "POST"])
def fl_web_user_upload_app(**url_params):
    return EndpointExecutor(UserUploadAppEndpoint, url_params).execute()
```

---

## 4. Index Page Changes

### 4.1 "Upload App" button

- Show "Upload App" button (green, plus-square icon) next to "Add a new app"
- Only visible to logged-in users (has_at_least_user_privileges)
- "Add a new app" (admin only) remains separate

### 4.2 App listing table changes

| Current | New |
|---------|-----|
| # | # |
| Icon | Icon |
| App name | App name |
| **Price** | **NEW** - "Free" or "$X.XX" or "0.XXX XMR" |
| **Owner** | **NEW** - owner_username (displayed as username, resolved from FK → user_account) |
| Actions | Actions |

### 4.3 App details page changes

- Show price section with:
  - Price in chosen currency
  - Price in alternative currency (converted at current rate, with "approx." label)
  - Owner name
- If paid: show "Download" button that triggers payment flow
- If free: download works as-is

---

## 5. Payment Flow

### 5.1 Payment states for a paid app download

```
User clicks "Download"
  → Check if app is free
    → YES: download APK immediately (existing flow)
    → NO: create sale record → generate XMR invoice → show payment page
```

### 5.2 Payment page

When a user clicks "Download" on a paid app:

1. Create `app_sale` record with status "pending"
2. If currency is XMR:
   - Use existing `MoneroGateway` to create invoice address
   - Convert USD price to XMR if needed
   - Show: subaddress, amount in XMR, QR code (monero: URI)
   - Poll payment status every 10 seconds
3. If currency is USD:
   - TODO: determine payment processor (Stripe? PayPal? manual?)

### 5.3 Payment confirmation

- When payment is confirmed (XMR received + confirmations met):
  - Update `app_sale` status to "confirmed"
  - Issue download link (temporary URL, expires after 24h)
  - Redirect user to download
- If payment expires: show "payment expired" message, allow retry

### 5.4 New files needed

| File | Purpose |
|------|---------|
| `src/selfdroid/web/endpoints/PaymentCreateInvoiceEndpoint.py` | Create XMR invoice for app purchase |
| `src/selfdroid/web/endpoints/PaymentCheckStatusEndpoint.py` | Poll endpoint for payment status |
| `src/selfdroid/web/endpoints/PaymentDownloadEndpoint.py` | Issue download after payment confirmed |
| `src/selfdroid/web/templates/payment_page.html` | Payment page with QR code, amount, status |

### 5.5 New routes

```python
@web_blueprint.route("/payment/create-invoice/<int:app_id>", methods=["POST"])
def fl_web_payment_create_invoice(**url_params)

@web_blueprint.route("/payment/check-status/<int:sale_id>", methods=["GET"])
def fl_web_payment_check_status(**url_params)

@web_blueprint.route("/payment/download/<int:sale_id>", methods=["GET"])
def fl_web_payment_download(**url_params)
```

---

## 6. Admin Approval Flow

### 6.1 New admin page: "Pending submissions"

- List all apps with `is_approved=False`
- Show: app name, icon, uploaded_by, price, date submitted
- Actions per submission: Approve / Reject
- If rejected: optional rejection reason

### 6.2 New admin endpoint

| File | Purpose |
|------|---------|
| `src/selfdroid/web/endpoints/AdminPendingSubmissionsEndpoint.py` | List pending submissions |
| `src/selfdroid/web/endpoints/AdminApproveAppEndpoint.py` | Approve an app (sets is_approved=True, is_published=True) |
| `src/selfdroid/web/endpoints/AdminRejectAppEndpoint.py` | Reject an app (sets is_approved=False, is_published=False) |
| `src/selfdroid/web/templates/admin_pending_submissions.html` | Admin review page |

### 6.3 New admin route

```python
@web_blueprint.route("/admin/pending", methods=["GET"])
def fl_web_admin_pending(**url_params)

@web_blueprint.route("/admin/approve/<int:app_id>", methods=["POST"])
def fl_web_admin_approve(**url_params)

@web_blueprint.route("/admin/reject/<int:app_id>", methods=["POST"])
def fl_web_admin_reject(**url_params)
```

### 6.4 Admin nav changes

Add "Pending" link to admin navbar that goes to `/web/admin/pending`

---

## 7. Download Endpoint Changes

### 7.1 `WebDownloadAPKEndpoint` modifications

Current logic:
```
authenticated user → download APK
```

New logic:
```
authenticated user → get app metadata
  → if app is_published AND (is_free OR price == 0):
      download APK (existing behavior)
  → if paid app:
      check if user has confirmed sale for this app
        → YES: download APK
        → NO: redirect to payment page
  → if not published:
      404 (same as current behavior for unpublished)
```

### 7.2 Sale verification

When checking if a user can download a paid app:
- Look up `app_sale` record where `app_id = X` and `buyer_user_id = current_user_id` and `payment_status = "confirmed"`
- If no confirmed sale exists, redirect to payment flow

---

## 8. API Changes

### 8.1 `AppMetadataDBModel.to_api_dict()` additions

New fields in API response:
```python
"price_usd": ...,
"price_xmr": ...,
"currency": ...,
"owner_username": ...,
"owner_user_id": ...,
"is_published": ...,
```

### 8.2 New API endpoint for payment

```python
# GET /api/v1/payment/invoice/<int:app_id>?buyer_user_id=1
# Returns: { "subaddress": "...", "amount_xmr": "...", "amount_usd": "...", "payment_uri": "..." }

# GET /api/v1/payment/status/<int:sale_id>
# Returns: { "status": "pending|confirmed|expired", "confirmations": 3, "required": 2 }
```

### 8.3 New API endpoint for app upload status

```python
# GET /api/v1/app/<int:app_id>/upload-status
# Returns: { "is_approved": True/False, "is_published": True/False, "rejection_reason": "..." }
```

---

## 9. Settings / Configuration Changes

### 9.1 New settings in `Settings.py`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `USER_UPLOAD_ENABLED` | bool | `False` | Feature flag for user uploads |
| `USER_UPLOAD_REQUIRES_APPROVAL` | bool | `True` | Admin approval required before publishing |
| `MIN_PRICE_USD` | Decimal | `0.01` | Minimum app price in USD |
| `MIN_PRICE_XMR` | Decimal | `0.001` | Minimum app price in XMR |
| `DOWNLOAD_EXPIRY_HOURS` | int | `24` | How long download links remain valid |
| `ALLOWED_USER_UPLOAD_DOMAINS` | list | `[]` | If set, only emails from these domains can upload |

### 9.2 Environment variables

| Variable | Description |
|----------|-------------|
| `SELFDROID_USER_UPLOAD_ENABLED` | Override `USER_UPLOAD_ENABLED` |
| `SELFDROID_MIN_PRICE_USD` | Override `MIN_PRICE_USD` |
| `SELFDROID_MIN_PRICE_XMR` | Override `MIN_PRICE_XMR` |

---

## 10. Summary of New Files

### User accounts

1. `src/selfdroid/appstorage/UserAccountDBModel.py` - User account model
2. `src/selfdroid/web/forms/UserAccountLoginForm.py` - Login form for dedicated user accounts
3. `src/selfdroid/web/forms/UserAdminCreateAccountForm.py` - Admin form to create new user accounts
4. `src/selfdroid/web/endpoints/UserLoginEndpoint.py` - Login endpoint for dedicated accounts
5. `src/selfdroid/web/endpoints/UserAdminCreateAccountEndpoint.py` - Admin endpoint to create accounts
6. `src/selfdroid/web/endpoints/UserAdminManageAccountsEndpoint.py` - Admin page to manage accounts
7. `src/selfdroid/web/templates/admin_user_accounts.html` - Admin account management page
8. `src/selfdroid/web/templates/web_user_login.html` - User login page (separate from shared password login)
9. `src/selfdroid/appstorage/crud/UserAccountManager.py` - CRUD operations for user accounts

### Core (upload + pricing)

1. `src/selfdroid/web/forms/UserUploadAppForm.py`
2. `src/selfdroid/web/endpoints/UserUploadAppEndpoint.py`
3. `src/selfdroid/web/templates/web_user_upload.html`
4. `src/selfdroid/appstorage/crud/AppUploader.py`

### Payment

5. `src/selfdroid/web/endpoints/PaymentCreateInvoiceEndpoint.py`
6. `src/selfdroid/web/endpoints/PaymentCheckStatusEndpoint.py`
7. `src/selfdroid/web/endpoints/PaymentDownloadEndpoint.py`
8. `src/selfdroid/web/templates/payment_page.html`
9. `src/selfdroid/appstorage/crud/AppSaleManager.py`

### Admin approval

10. `src/selfdroid/web/endpoints/AdminPendingSubmissionsEndpoint.py`
11. `src/selfdroid/web/endpoints/AdminApproveAppEndpoint.py`
12. `src/selfdroid/web/endpoints/AdminRejectAppEndpoint.py`
13. `src/selfdroid/web/templates/admin_pending_submissions.html`

### Models

14. (Modify) `src/selfdroid/appstorage/AppMetadataDBModel.py` - add new columns
15. (Modify) `src/selfdroid/payments/invoice.py` - add `AppSale` model

### API

16. (Modify) `src/selfdroid/api/v1/endpoints/APIv1AppDetailsEndpoint.py` - add fields
17. (Modify) `src/selfdroid/api/v1/endpoints/APIv1AllAppDetailsEndpoint.py` - add fields
18. (Modify) `src/selfdroid/api/v1/APIv1EndpointBase.py` - add payment routes
19. (Modify) `src/selfdroid/api/__init__.py` - register new endpoints

### Config

20. (Modify) `src/selfdroid/Settings.py` - add new settings
21. (Modify) `src/selfdroid/web/WebHelpers.py` - add upload button context
22. (Modify) `src/selfdroid/web/__init__.py` - register new routes

### Template changes

23. (Modify) `src/selfdroid/web/templates/web_index.html` - add upload button + price/owner columns
24. (Modify) `src/selfdroid/web/templates/web_app_details.html` - add price + payment flow
25. (Modify) `src/selfdroid/web/templates/_web_base.html` - add admin pending nav link

---

## 11. Implementation Order (Recommended)

1. **Schema changes** - Add `user_account` table, add FK columns to `AppMetadataDBModel`, create `app_sale` table
2. **User account models + CRUD** - `UserAccountDBModel`, `UserAccountManager`
3. **Admin account creation** - Admin page to create/manage user accounts
4. **User login** - Login form + endpoint for dedicated user accounts
5. **Schema extensions** - Add price/approval columns to `AppMetadataDBModel`
6. **User upload form + endpoint** - Basic upload without pricing
7. **Add price fields** - Extend upload form with price/currency
8. **Index page updates** - Show price, owner, upload button
9. **Admin approval** - Pending submissions page + approve/reject
10. **Payment flow** - XMR invoice + payment page
11. **Download flow** - Integrate payment check into download endpoint
12. **API updates** - Add new fields to API responses
13. **Settings/config** - Feature flags, environment variables
14. **Polish** - Error messages, edge cases, UX improvements

---

## 12. Open Questions / Decisions Needed

1. **User login page**: Should dedicated user login be on the same page as shared password login, or a separate page?
2. **Admin account creation**: Should admin set the password directly, or auto-generate and email it to the user?
3. **Password reset**: Can users reset their own password, or must admin do it?
4. **USD payments**: What payment processor for USD? (Stripe, PayPal, manual bank transfer?)
5. **Upload limit**: Should there be a per-user upload limit? (e.g., max 5 submissions)
6. **Revenue split**: Does the platform take a cut of paid app sales?
7. **Refund policy**: What happens if a user pays but the app is later removed?
8. **Upload via API**: Should the public API support app upload (not just web)?
9. **Intermediate model**: Do we need `UploadedApp` as a staging table, or go straight to `app_metadata` with `is_approved=False`?
10. **Price updates**: Can users change the price after uploading?
11. **Currency conversion display**: Should we always show both USD and XMR prices on the details page?
12. **QR code library**: Do we have a Python QR code library, or need to add one? (python-qrcode + Pillow)
13. **Account deactivation**: When an account is deactivated, what happens to their uploaded apps? (keep, delete, or transfer?)
14. **Bulk account creation**: Should admin be able to upload a CSV to create multiple accounts at once?
