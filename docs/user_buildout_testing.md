# User App Upload & Payment Buildout — Testing Guide

This document lists recommended unit and integration tests for all new and modified code.

---

## 1. Database Models

### UserAccountDBModel

| Test | Type | Description |
|------|------|-------------|
| `test_create_user_account_columns` | Unit | Verify all columns exist with correct types, nullable, defaults |
| `test_username_unique_constraint` | Unit | Verify duplicate username raises integrity error |
| `test_password_hash_storage` | Unit | Verify password_hash is stored as string (bcrypt) |
| `test_is_active_default` | Unit | Verify is_active defaults to True |
| `test_created_at_default` | Unit | Verify created_at defaults to NOW |
| `test_created_by_fk` | Unit | Verify created_by references user_account.id |

### AppSaleDBModel

| Test | Type | Description |
|------|------|-------------|
| `test_create_app_sale_columns` | Unit | Verify all columns exist with correct types, nullable, defaults |
| `test_payment_status_default` | Unit | Verify payment_status defaults to "pending" |
| `test_currency_default` | Unit | Verify currency defaults to "usd" |
| `test_is_expired_pending` | Unit | Verify is_expired() returns False for pending sales |
| `test_is_expired_after_download_issued` | Unit | Verify is_expired() returns True after 24h from download_issued_at |
| `test_to_dict_output` | Unit | Verify to_dict() returns correct keys and values |
| `test_app_id_fk` | Unit | Verify app_id references app_metadata.id |
| `test_buyer_user_id_fk` | Unit | Verify buyer_user_id references user_account.id |

### AppMetadataDBModel (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_new_columns_exist` | Unit | Verify all 10 new columns exist on app_metadata table |
| `test_uploaded_by_nullable` | Unit | Verify uploaded_by defaults to NULL |
| `test_owner_username_nullable` | Unit | Verify owner_username defaults to NULL |
| `test_price_usd_nullable` | Unit | Verify price_usd defaults to NULL |
| `test_price_xmr_nullable` | Unit | Verify price_xmr defaults to NULL |
| `test_currency_default_usd` | Unit | Verify currency defaults to "usd" |
| `test_is_published_default_false` | Unit | Verify is_published defaults to False |
| `test_is_approved_default_false` | Unit | Verify is_approved defaults to False |
| `test_approved_by_nullable` | Unit | Verify approved_by defaults to NULL |
| `test_approved_at_nullable` | Unit | Verify approved_at defaults to NULL |
| `test_rejection_reason_nullable` | Unit | Verify rejection_reason defaults to NULL |

---

## 2. CRUD Layer

### UserAccountManager

| Test | Type | Description |
|------|------|-------------|
| `test_create_account_success` | Unit | Verify account is created with correct username, hash, created_by |
| `test_create_account_duplicate_username` | Unit | Verify ValueError raised for duplicate username |
| `test_authenticate_valid_credentials` | Unit | Verify authenticate() returns account for correct username/password |
| `test_authenticate_invalid_password` | Unit | Verify authenticate() returns None for wrong password |
| `test_authenticate_nonexistent_user` | Unit | Verify authenticate() returns None for nonexistent username |
| `test_authenticate_deactivated_account` | Unit | Verify authenticate() returns None for deactivated account |
| `test_get_by_id_valid` | Unit | Verify get_by_id() returns account for valid ID |
| `test_get_by_id_invalid` | Unit | Verify get_by_id() returns None for invalid ID |
| `test_get_by_username_valid` | Unit | Verify get_by_username() returns account for valid username |
| `test_get_by_username_invalid` | Unit | Verify get_by_username() returns None for invalid username |
| `test_get_all_accounts` | Unit | Verify get_all_accounts() returns all accounts ordered by created_at desc |
| `test_deactivate_account` | Unit | Verify deactivate_account() sets is_active=False |
| `test_deactivate_account_nonexistent` | Unit | Verify deactivate_account() returns False for nonexistent ID |
| `test_reset_password` | Unit | Verify reset_password() updates password_hash |
| `test_reset_password_nonexistent` | Unit | Verify reset_password() returns False for nonexistent ID |
| `test_delete_account` | Unit | Verify delete_account() removes account and associated apps |
| `test_delete_account_nonexistent` | Unit | Verify delete_account() returns False for nonexistent ID |
| `test_change_password_for_self_valid` | Unit | Verify change_password_for_self() succeeds with correct old password |
| `test_change_password_for_self_wrong_old` | Unit | Verify change_password_for_self() fails with wrong old password |
| `test_change_password_for_self_nonexistent` | Unit | Verify change_password_for_self() returns False for nonexistent ID |

### AppSaleManager

| Test | Type | Description |
|------|------|-------------|
| `test_create_sale` | Unit | Verify create_sale() creates record with correct fields |
| `test_get_by_id_valid` | Unit | Verify get_by_id() returns sale for valid ID |
| `test_get_by_id_invalid` | Unit | Verify get_by_id() returns None for invalid ID |
| `test_get_by_app_and_user_confirmed` | Unit | Verify get_by_app_and_user() returns sale for confirmed payment |
| `test_get_by_app_and_user_pending` | Unit | Verify get_by_app_and_user() returns None for pending payment |
| `test_confirm_sale` | Unit | Verify confirm_sale() sets status=confirmed, sets download_issued_at |
| `test_confirm_sale_nonexistent` | Unit | Verify confirm_sale() returns None for nonexistent ID |
| `test_expire_sale` | Unit | Verify expire_sale() sets status=expired |
| `test_expire_sale_nonexistent` | Unit | Verify expire_sale() returns None for nonexistent ID |
| `test_get_pending_sales` | Unit | Verify get_pending_sales() returns only pending sales |
| `test_get_sales_for_user` | Unit | Verify get_sales_for_user() returns only that user's sales |

---

## 3. Web Endpoints — User Account Management

### UserAdminCreateAccountEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_requires_admin` | Integration | Verify GET returns redirect/403 for non-admin |
| `test_post_creates_account` | Integration | Verify POST creates account with given username/password |
| `test_post_duplicate_username` | Integration | Verify POST shows error for duplicate username |
| `test_post_invalid_form` | Integration | Verify POST shows form errors for invalid input |

### UserAdminManageAccountsEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_requires_admin` | Integration | Verify GET returns redirect/403 for non-admin |
| `test_get_lists_accounts` | Integration | Verify GET renders template with all accounts |
| `test_deactivate_action` | Integration | Verify ?action=deactivate sets is_active=False |
| `test_activate_action` | Integration | Verify ?action=activate sets is_active=True |
| `test_reset_password_action` | Integration | Verify ?action=reset_password with valid form updates password |
| `test_delete_action` | Integration | Verify ?action=delete removes account and associated apps |

### UserLoginEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_shows_form` | Integration | Verify GET renders login form |
| `test_post_valid_login` | Integration | Verify POST with valid credentials sets session + redirects to index |
| `test_post_invalid_password` | Integration | Verify POST with wrong password shows error + re-renders form |
| `test_post_nonexistent_user` | Integration | Verify POST with nonexistent username shows error |
| `test_post_deactivated_user` | Integration | Verify POST with deactivated account shows error |
| `test_post_invalid_form` | Integration | Verify POST with empty fields shows form errors |

---

## 4. Web Endpoints — User Upload

### UserUploadAppEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_requires_user` | Integration | Verify GET redirects for anonymous user |
| `test_get_shows_form` | Integration | Verify GET renders upload form |
| `test_post_valid_upload` | Integration | Verify POST creates app_metadata with is_approved=False, is_published=False |
| `test_post_sets_uploaded_by` | Integration | Verify uploaded_by FK is set to current user_account_id |
| `test_post_sets_owner_username` | Integration | Verify owner_username is set to current user's username |
| `test_post_sets_price_usd` | Integration | Verify price_usd is set from form |
| `test_post_sets_price_xmr` | Integration | Verify price_xmr is calculated from price_usd via exchange rate |
| `test_post_currency_selector` | Integration | Verify currency field is stored correctly |
| `test_post_free_app` | Integration | Verify empty price results in NULL price_usd and price_xmr |
| `test_post_duplicate_package_name` | Integration | Verify POST shows error for duplicate package name |
| `test_post_invalid_apk` | Integration | Verify POST shows error for invalid APK file |
| `test_post_invalid_form` | Integration | Verify POST with missing fields shows form errors |

---

## 5. Web Endpoints — Admin Approval

### AdminPendingSubmissionsEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_requires_admin` | Integration | Verify GET redirects for non-admin |
| `test_get_shows_pending` | Integration | Verify GET renders template with is_approved=False apps |
| `test_get_empty_list` | Integration | Verify GET shows "no pending" message when list is empty |

### AdminApproveAppEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_post_requires_admin` | Integration | Verify POST redirects for non-admin |
| `test_post_approves_app` | Integration | Verify POST sets is_approved=True, is_published=True |
| `test_post_sets_approved_by` | Integration | Verify approved_by FK is set to admin user_account_id |
| `test_post_sets_approved_at` | Integration | Verify approved_at is set to current timestamp |
| `test_post_nonexistent_app` | Integration | Verify POST returns 404 for nonexistent app |
| `test_post_redirects_to_pending` | Integration | Verify POST redirects to /web/admin/pending |

### AdminRejectAppEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_post_requires_admin` | Integration | Verify POST redirects for non-admin |
| `test_post_rejects_app` | Integration | Verify POST sets is_approved=False, is_published=False |
| `test_post_sets_rejection_reason` | Integration | Verify rejection_reason is stored from form |
| `test_post_optional_reason` | Integration | Verify rejection_reason can be empty |
| `test_post_nonexistent_app` | Integration | Verify POST returns 404 for nonexistent app |
| `test_post_redirects_to_pending` | Integration | Verify POST redirects to /web/admin/pending |

---

## 6. Web Endpoints — Payment Flow

### PaymentCreateInvoiceEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_requires_user` | Integration | Verify GET redirects for anonymous user |
| `test_get_free_app_redirects` | Integration | Verify GET on free app redirects to app details with error |
| `test_get_creates_sale` | Integration | Verify GET creates app_sale with status=pending |
| `test_get_generates_subaddress` | Integration | Verify MoneroGateway.create_invoice_address is called |
| `test_get_shows_payment_page` | Integration | Verify GET renders payment_page.html with correct context |
| `test_get_nonexistent_app` | Integration | Verify GET returns 404 for nonexistent app |
| `test_post_creates_invoice` | Integration | Verify POST creates invoice (same as GET) |

### PaymentCheckStatusEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_nonexistent_sale` | Integration | Verify GET returns JSON with error for nonexistent sale |
| `test_get_pending_sale` | Integration | Verify GET returns status=pending for unconfirmed sale |
| `test_get_confirmed_sale` | Integration | Verify GET returns status=confirmed for confirmed sale |
| `test_get_auto_confirms` | Integration | Verify GET auto-confirms sale when payment detected |
| `test_get_calls_gateway` | Integration | Verify MoneroGateway.check_payment is called with correct params |

### PaymentDownloadEndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_no_confirmed_sale` | Integration | Verify GET redirects to payment for unconfirmed sale |
| `test_get_confirmed_sale` | Integration | Verify GET serves APK for confirmed sale |
| `test_get_nonexistent_sale` | Integration | Verify GET shows error for nonexistent sale |
| `test_get_nonexistent_app` | Integration | Verify GET returns 404 for nonexistent app |

### PaymentQREndpoint

| Test | Type | Description |
|------|------|-------------|
| `test_get_returns_png` | Integration | Verify GET returns PNG image with correct mimetype |
| `test_get_nonexistent_sale` | Integration | Verify GET returns 404 for nonexistent sale |
| `test_get_qr_content` | Integration | Verify QR code contains valid monero: URI |

---

## 7. Download Flow Changes

### WebDownloadAPKEndpoint (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_download_free_app` | Integration | Verify APK is served for free app |
| `test_download_paid_confirmed` | Integration | Verify APK is served for paid app with confirmed sale |
| `test_download_paid_unconfirmed` | Integration | Verify redirect to payment for paid app without confirmed sale |
| `test_download_unpublished` | Integration | Verify 404 for unpublished app |
| `test_download_nonexistent_app` | Integration | Verify 404 for nonexistent app |

---

## 8. AppMetadata Model Changes

### AppMetadata (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_is_free_true` | Unit | Verify is_free returns True when price_usd is NULL |
| `test_is_free_zero` | Unit | Verify is_free returns True when price_usd is 0 |
| `test_is_free_false` | Unit | Verify is_free returns False when price_usd > 0 |
| `test_to_api_dict_includes_new_fields` | Unit | Verify to_api_dict() includes all new pricing/ownership fields |
| `test_to_api_dict_price_usd_none` | Unit | Verify price_usd is None in API dict when not set |
| `test_to_api_dict_owner_username` | Unit | Verify owner_username is included in API dict |
| `test_to_api_dict_is_published` | Unit | Verify is_published is included in API dict |
| `test_to_api_dict_is_approved` | Unit | Verify is_approved is included in API dict |

---

## 9. Authenticator Changes

### WebAuthenticator (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_log_in_as_user_account` | Unit | Verify log_in_as_user_account() sets session vars correctly |
| `test_log_in_as_user_account_already_logged` | Unit | Verify log_in_as_user_account() raises exception if already logged in |
| `test_log_out_clears_user_account` | Unit | Verify log_out() clears user_account_id and user_account_username |

---

## 10. WebHelpers Changes

### WebHelpers (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_context_includes_user_account_id` | Unit | Verify template context includes user_account_id when logged in |
| `test_context_includes_user_account_username` | Unit | Verify template context includes user_account_username when logged in |
| `test_context_excludes_user_account_when_anonymous` | Unit | Verify user_account_id is None when not logged in |

---

## 11. Settings Changes

### Settings (modified)

| Test | Type | Description |
|------|------|-------------|
| `test_user_upload_enabled_default` | Unit | Verify USER_UPLOAD_ENABLED defaults to True |
| `test_user_upload_enabled_from_env` | Unit | Verify USER_UPLOAD_ENABLED respects SELFDROID_USER_UPLOAD_ENABLED |
| `test_user_upload_requires_approval_default` | Unit | Verify USER_UPLOAD_REQUIRES_APPROVAL defaults to True |
| `test_min_price_usd_default` | Unit | Verify get_min_price_usd() returns Decimal("0.01") |
| `test_min_price_usd_from_env` | Unit | Verify get_min_price_usd() respects SELFDROID_MIN_PRICE_USD |
| `test_min_price_xmr_default` | Unit | Verify get_min_price_xmr() returns Decimal("0.001") |
| `test_min_price_xmr_from_env` | Unit | Verify get_min_price_xmr() respects SELFDROID_MIN_PRICE_XMR |
| `test_download_expiry_hours_default` | Unit | Verify DOWNLOAD_EXPIRY_HOURS defaults to 24 |

---

## 12. Integration / End-to-End Tests

| Test | Type | Description |
|------|------|-------------|
| `e2e_admin_creates_user` | E2E | Admin creates user account → user logs in → session is valid |
| `e2e_user_uploads_app` | E2E | User uploads APK → app appears in pending → admin approves → app is published |
| `e2e_user_uploads_paid_app` | E2E | User uploads app with price → buyer sees price → creates invoice → pays → downloads |
| `e2e_admin_rejects_app` | E2E | Admin rejects submission → app not published → uploader notified |
| `e2e_download_enforcement` | E2E | Anonymous user cannot download paid app without payment |
| `e2e_account_deactivation` | E2E | Admin deactivates user → user cannot log in → apps deleted |
| `e2e_password_reset_admin` | E2E | Admin resets user password → user logs in with new password |
| `e2e_password_reset_self` | E2E | User changes own password → logs in with new password |
| `e2e_currency_conversion` | E2E | User sets USD price → price_xmr is calculated correctly |
| `e2e_free_app_no_payment` | E2E | Free app downloads without payment flow |
| `e2e_index_shows_price` | E2E | Index page displays price and owner columns |
| `e2e_app_details_shows_price` | E2E | App details page displays price, owner, and payment button |
| `e2e_nav_admin_links` | E2E | Admin sees Pending and Accounts nav links |
| `e2e_nav_user_upload_button` | E2E | Logged-in user sees Upload App button on index |

---

## Test Execution

### Unit Tests
```bash
cd src
python3 -m pytest tests/ -v --tb=short
```

### Integration Tests (requires running app)
```bash
cd src
python3 -m pytest tests/integration/ -v --tb=short --run-integration
```

### E2E Tests (requires running app + Monero testnet)
```bash
cd src
python3 -m pytest tests/e2e/ -v --tb=long --run-e2e
```

### Test Coverage
```bash
cd src
python3 -m pytest tests/ --cov=selfdroid --cov-report=html --cov-report=term-missing
```
