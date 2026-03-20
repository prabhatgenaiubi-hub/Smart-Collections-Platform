# Outreach Credentials Setup Guide

Complete guide to set up real sending for the Digital Outreach Agent.  
Until you add credentials, everything runs in **mock mode** — messages are logged to the console and flagged `mock_sent`. No real messages are sent.

---

## Environment Variables (add to `.env` in project root)

```env
# ── WhatsApp (Meta Cloud API) ───────────────────────────────
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# ── Email (SMTP) ────────────────────────────────────────────
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
```

---

## Part 1 — WhatsApp (Meta Cloud API)

### What you need
- A Meta Developer account (free)
- A Meta Business account (free)
- A WhatsApp Business phone number

### Step-by-step

#### 1. Create a Meta Developer account
1. Go to **https://developers.facebook.com**
2. Click **Get Started** and sign in with your Facebook / Meta account
3. Accept the developer terms

#### 2. Create a Meta Business account (if you don't have one)
1. Go to **https://business.facebook.com**
2. Click **Create Account**
3. Fill in your business name and details
4. Verify your business email

#### 3. Create a Meta Developer App
1. Go to **https://developers.facebook.com/apps**
2. Click **Create App**
3. Choose **Business** as the app type
4. Give it a name (e.g. `Smart Collections Platform`)
5. Link it to your Meta Business account
6. Click **Create App**

#### 4. Add WhatsApp product to your app
1. In your app dashboard, scroll to **Add Products to Your App**
2. Find **WhatsApp** and click **Set Up**
3. You will be prompted to link a WhatsApp Business Account (WABA)
   - If you don't have one, Meta will create a test WABA for you

#### 5. Get your Phone Number ID
1. In your app → **WhatsApp** → **API Setup**
2. Under **From**, you will see a test phone number
3. Copy the **Phone Number ID** shown below it
4. Paste it as:
   ```
   WHATSAPP_PHONE_NUMBER_ID=<paste here>
   ```

#### 6. Get your Access Token

**For testing (temporary token — expires in ~24h):**
1. In WhatsApp → API Setup
2. You will see a **Temporary access token**
3. Copy it and paste as:
   ```
   WHATSAPP_ACCESS_TOKEN=<paste here>
   ```

**For production (permanent token — recommended):**
1. Go to **https://business.facebook.com** → **Settings** → **System Users**
2. Create a **System User** with Admin role
3. Assign your app to the system user
4. Click **Generate Token** → select your app → check WhatsApp permissions
5. Copy the token and paste as `WHATSAPP_ACCESS_TOKEN`

#### 7. Add a test recipient
1. In WhatsApp → API Setup → **To** field
2. Click **Manage phone number list**
3. Add your mobile number (with country code e.g. `+919876543210`)
4. Verify the OTP sent to your phone
5. You can now send test messages to that number

#### 8. Verify it works
Run a quick test using the Meta API Explorer or the Postman collection from Meta's docs.  
Once sending works there, your credentials will work in this application.

> **Free tier note**: Meta gives 1,000 free business-initiated conversations per month per WABA in most regions. After that, per-message pricing applies.

---

## Part 2 — Email via SMTP

You have two good options:

---

### Option A: Gmail (easiest for development)

**Required: 2-Step Verification must be enabled on your Google account.**

#### Steps
1. Go to **https://myaccount.google.com/security**
2. Under **2-Step Verification**, ensure it is enabled
3. Go to **https://myaccount.google.com/apppasswords**
   - Search for "App passwords" if you don't see it directly
4. Under **Select app**, choose **Mail**
5. Under **Select device**, choose **Other (Custom name)**
6. Enter a name like `Smart Collections`
7. Click **Generate**
8. Copy the 16-character password shown (spaces don't matter)

#### Environment variables
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail-address@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # the 16-char app password
SMTP_FROM_EMAIL=your-gmail-address@gmail.com
```

> **Free tier note**: Gmail SMTP has no hard sending limit for personal/low-volume use. For bulk/transactional, move to Brevo.

---

### Option B: Brevo (formerly Sendinblue) — free 300 emails/day

Brevo is better for transactional sending at scale and has a generous free tier.

#### Steps
1. Create a free account at **https://www.brevo.com**
2. Verify your email address
3. Go to **Account** → **SMTP & API** (or search for SMTP in settings)
4. You will see:
   - **SMTP Server**: `smtp-relay.brevo.com`
   - **Port**: `587`
   - **Login**: your Brevo account email
   - **Password / SMTP Key**: click **Generate a new SMTP key**
5. Copy the SMTP key

#### Environment variables
```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your-brevo-login@email.com
SMTP_PASSWORD=<your-brevo-smtp-key>
SMTP_FROM_EMAIL=your-verified-sender@email.com
```

> **Important**: The `SMTP_FROM_EMAIL` must be a verified sender in Brevo (go to **Senders & IPs** → add and verify your email/domain).

> **Free tier note**: Brevo gives 300 emails/day free with no credit card required.

---

## Part 3 — After adding credentials

1. Add variables to your `.env` file in the project root
2. Restart the backend server:
   ```powershell
   uvicorn backend.main:app --reload --port 8000
   ```
3. Log in as a bank officer
4. Go to **📡 Digital Outreach** tab
5. Search for a customer → select loan → choose channel → Generate Draft → Edit → Send
6. Check:
   - Status badge should show **✅ Sent** (not 🟡 Mock Sent)
   - WhatsApp: message appears on the test phone
   - Email: message arrives in the inbox

---

## Part 4 — Mock mode (no credentials)

If you have not added credentials yet:
- Everything still works
- Status shows **🟡 Mock Sent (no credentials)**
- Message is printed to the backend console/logs
- History still records the event with `status: mock_sent`
- Officer edit (HITL) still works exactly the same

This means you can demo and test the full flow without real API keys.

---

## Security reminders

- Never commit your `.env` file to git (it is already in `.gitignore`)
- For WhatsApp production, use a permanent system user token, not the temporary one
- Rotate tokens regularly
- For email production, use a dedicated sender domain (not Gmail personal)
- Always test with one real recipient before sending to all customers
