# Future Development

This document tracks features and improvements that are planned but not yet implemented.

## 1. Per-User Upload Limits

Implement a per-user upload limit (e.g., max 5 submissions at a time). This would require:

- Adding an `upload_count` field to `user_account` or a separate `user_upload_limit` table
- Checking the count in `UserUploadAppEndpoint` before allowing a new upload
- Resetting the count when submissions are approved or rejected
- Admin override capability

## 2. Revenue Split / Platform Fee

Implement a platform fee on paid app sales:

- Add a `platform_fee_percentage` setting (e.g., 10%)
- Track net amount owed to app owner in `app_sale`
- Add admin revenue dashboard
- Implement payout mechanism

## 3. App Refund Policy

Define and implement a refund policy for paid apps:

- Add `refund_requested` and `refund_status` fields to `app_sale`
- Admin refund approval workflow
- Refund processing via Monero wallet

## 4. Public API App Upload

Allow app upload via the public API:

- Add API endpoint for APK upload with authentication
- Support API key management per user
- Rate limiting for API uploads

## 5. App Owner Management

Allow app owners to manage their apps:

- Add `AppOwner` model for ownership management
- Owner can update app name, description, price
- Owner can take app down (unpublish)
- Owner can view their sale statistics
- Admin can reassign ownership

## 6. USD Payment Processor

Implement USD payment processing (currently only XMR):

- Stripe integration
- PayPal integration
- Manual bank transfer option

## 7. Bulk Account Creation via CSV

Allow admin to upload a CSV to create multiple user accounts at once:

- CSV format: `username,password`
- Admin endpoint to parse and create accounts
- Error reporting for invalid rows

## 8. Password Reset for Logged-in Users

Allow users to reset their own password after logging in:

- Add password change form to user profile
- Verify old password before allowing change
- Email notification on password change (future)

## 9. User Profile Page

Add a user profile page:

- View account info
- Change password
- View uploaded apps and their status
- View purchase history

## 10. Email Notifications

Add email notifications for:

- New app submission (notify admin)
- App approved/rejected (notify user)
- Payment confirmed (notify user)
- Password reset

## 11. App Version Management

Allow app owners to manage app versions:

- View all versions of their apps
- Delete old versions
- Rollback to previous version

## 12. Analytics Dashboard

Add analytics for:

- Total downloads per app
- Total revenue per app
- Total revenue overall
- User growth
- Payment status overview
