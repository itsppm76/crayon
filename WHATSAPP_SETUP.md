# Crayon on WhatsApp

Same Crayon (same brain, tools, database and safety rules), a second channel. Telegram keeps working.
The webhook is served by the existing `main.py` at `/whatsapp/webhook`. No extra process, no Flask.

A WhatsApp person is a separate Crayon user (their number is their id). Memory, notes, reminders and Google
connections are not shared with a Telegram account. Only numbers in `CRAYON_OWNER_WA_ID` / `WHATSAPP_ALLOWED_IDS`
get replies; everyone else is ignored silently.

## What is already done on Meta's side
- App "Crayon Assistant" (App ID 1108783611591512), test number +1 (555) 651-8301, Phone Number ID 1319365061266564
- Your number +91 87775 66396 is verified as a recipient (max 5 recipients on the test number)

## Setup (about 5 minutes)
1. Set these environment variables where Crayon runs (Render > Environment, or your local `.env`). Secrets are in your Instinct vault:
   - `WHATSAPP_ACCESS_TOKEN` = vault entry "Meta WhatsApp temp access token"
   - `WHATSAPP_APP_SECRET` = vault entry "Meta app secret (Crayon Assistant)"
   - `WHATSAPP_VERIFY_TOKEN` = any string you pick, for example `crayon-verify-2d7f91`
   - `WHATSAPP_PHONE_NUMBER_ID=1319365061266564`
   - `WHATSAPP_GRAPH_VERSION=v25.0`
   - `CRAYON_OWNER_WA_ID=918777566396`
2. Deploy or restart Crayon. Check `GET /health` returns ok.
3. Meta dashboard > Crayon Assistant > WhatsApp > Configuration > Webhook (https://developers.facebook.com/apps/1108783611591512/whatsapp-business/wa-settings/):
   - Callback URL = `<your public URL>/whatsapp/webhook`. On Render that is `https://crayon-v1.onrender.com/whatsapp/webhook` (your `CRAYON_PUBLIC_URL`).
   - Verify token = the same string as `WHATSAPP_VERIFY_TOKEN`. Click Verify and save.
   - Subscribe to the **messages** field.
4. From your WhatsApp, message +1 (555) 651-8301. Crayon replies.

Running locally instead: `pip install -r requirements.txt`, fill `.env`, `python main.py`, then expose port 10000 with
`cloudflared tunnel --url http://127.0.0.1:10000` and use that URL in step 3. Local runs need `TELEGRAM_BOT_TOKEN`,
`GEMINI_API_KEY` and `DATABASE_URL` as usual. Don't run the same bot token from two machines at once.

## Refresh the access token (about every 24 hours)
The temporary token expires after roughly a day. When replies stop and the logs say "token expired or invalid":
developers.facebook.com > app > WhatsApp > API setup > Generate access token, update `WHATSAPP_ACCESS_TOKEN`, restart.
For a token that does not expire: Business Settings > System users > add one, assign the app and the WhatsApp account,
generate a token with `whatsapp_business_messaging` and `whatsapp_business_management`.

## How it maps
- Text messages go through the same handler as Telegram private chats (commands like /tasks, /work, reminders, memory, research).
- Telegram buttons become WhatsApp reply buttons (up to 3) or a list (4 to 10). Email Send/Cancel and calendar Create/Cancel work the same way.
- Charts and files are sent as WhatsApp images or documents (2 MB cap, same as Telegram).
- Reminders and digests for a WhatsApp user are delivered on WhatsApp.

## Limits
- Free-form messages only work within 24 hours of your last message to the number. A reminder due later than that fails to send and is not retried. Message Crayon once a day, or add approved message templates (not built).
- Text, button taps and list picks only. Photos, voice and documents get "Text only on WhatsApp for now".
- No reactions, no message deletion (a pasted secret cannot be deleted for you; rotate it), no groups.
- The test number is for development. Check Meta's current pricing before using your own number.
- Reply keyboards (the Telegram menu buttons) are not shown on WhatsApp.
