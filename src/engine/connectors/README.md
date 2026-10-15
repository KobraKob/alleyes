# Connector Integration Guides & External Setup Requirements

This document outlines the real-world external credentials, verification, and setup processes required to graduate from dry-run mode to live production integrations.

---

## 1. WhatsApp Cloud API Connector (`whatsapp`)

### Required Credentials:
- `WHATSAPP_PHONE_NUMBER_ID`: Numerical ID of the verified phone number.
- `WHATSAPP_APP_SECRET`: App secret used to verify `X-Hub-Signature-256` HMAC signatures on incoming webhooks.
- `WHATSAPP_VERIFY_TOKEN`: Arbitrary token configured in Meta App Dashboard for webhook handshake verification.
- Permanent System User Access Token with `whatsapp_business_messaging` and `whatsapp_business_management` permissions.

### Regulatory & Platform Approvals Required:
1. **Meta Business Verification**: Must upload official business registration documents (e.g., GST certificate, certificate of incorporation) to Meta Business Manager.
2. **Display Name Approval**: Must match legal business name or registered trademark.
3. **Template Approval**: All outbound messages initiated outside the 24-hour customer service window require pre-approved message templates submitted through Meta Business Suite.

---

## 2. Meta Marketing API Connector (`meta_ads`)

### Required Credentials:
- `META_APP_ID`: Registered Meta developer application ID.
- `META_APP_SECRET`: Application secret for authentication.
- Ad Account ID (`act_<AD_ACCOUNT_ID>`).
- Long-lived System User Access Token with `ads_management` and `ads_read` permissions.

### Approvals Required:
1. **Meta App Review**: Request permissions for `ads_management` via Meta Developer Portal.
2. **Standard Access / Advanced Access**: Graduate app from Development mode to Live mode to create campaigns on production ad accounts.
3. **Payment Method Verification**: Valid credit line or card linked to the target Ad Account.

---

## 3. Email Connector (`ses`)

### Required Credentials:
- AWS Access Key ID & Secret Access Key (or IAM Role).
- `SES_REGION`: e.g. `ap-south-1` (Mumbai).
- Verified Domain Identity.

### Setup Steps:
1. **DKIM / SPF / DMARC DNS Records**: Add CNAME and TXT records to your domain's DNS provider to enable high deliverability.
2. **Production Access Request**: Request release from AWS SES Sandbox mode to allow sending to unverified recipients.
3. **List-Unsubscribe**: Configured in message headers per RFC 8058.

---

## 4. Google Business Profile (`gbp`)

### Required Credentials:
- Google Cloud Project with Google My Business API enabled.
- OAuth 2.0 Client ID and Client Secret.
- Refresh Token authorizing read access to business locations and reviews.
