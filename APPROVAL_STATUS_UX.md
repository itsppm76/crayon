# Approval and work-status UX staging

Native Crayon implementation inspired by the public approval-card interaction in OpenMausBot. No upstream source copied, no fork, enterprise code, React/Electron dependency, provider or payment added.

## Scope

- Web inline review cards for existing email/calendar/Sheet/create-file/form/fact actions. Exact server preview stays authoritative, HTML is sandboxed, edit creates a fresh ticket and supersedes prior pending tickets in the same owner/session. Confirm/cancel/expiry are one-use. Connection errors show unconfirmed, never success or automatic retry.
- Real progress events gain request-local step IDs and sequences. Repeated labels stay distinct; history/activity use the same display helper. No fabricated rotating status words or percent. Done is a returned provider/readback result, not a button click. Workspace content readback and visual acceptance remain distinct.
- Telegram keeps existing exact-review callback gates and typed fallback; action buttons say what will happen. Safe work labels update one bot status message, throttled to at most one edit per3seconds; no arguments/private data. Final response settles display without claiming an action was completed. Groups/WhatsApp do not gain new review permissions.
- All existing personal API/auth/private-read boundaries stay. Nothing repoints the Pages API. No runtime mounting of team staging ports or parity branch.

## Verification

Base a6bd554. Existing528 tests retained; one expected button-label assertion updated from Create to Create exactly this. New tests cover request sequences/repeated labels, awaiting review, throttle/no late edits, owner/session supersession and uncertain readback.

Run `python -m pytest -q` and `python check_approval_status_browser.py` with Playwright and Chrome installed. Browser checks are signed-in fixtures, never live provider sends. At390/1280: preview zero effects, edit new ticket, cancel correct ticket, escaped script text/sandbox HTML, repeated labels and unknown status, no page errors/overflow. Screenshots inspected after fixes to mobile menu, composer sizing and preview contrast. Local fixture cannot prove real external Create/Send acceptance.

Live base acceptance was completed separately using the owner's Telegram account and one harmless actual chat turn. This UX revision still needs exact-head review before merge and a staged deployment checkpoint. No live send/calendar/Sheet/form test was performed by this staging work.

## Limits

Review cards remain transient private views and are not stored in model/chat history. Clearing view does not cancel server pending review, but cannot approve it; tickets expire. Existing private-result isolation is deliberate. UI unknown results require checking destination, never a generated retry. Telegram edits are best-effort; the final response remains the durable receipt. SQL/provider lifecycle is unchanged except superseding pending reviews and explicit display outcomes. No guarantee of external delivery or file visual correctness.
