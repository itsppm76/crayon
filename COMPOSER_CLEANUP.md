# Composer cleanup

Visual and local-interaction redesign only, based on main1a00a2e.
One rounded boundary groups a full-width text lane and a quiet action row.
Upload and the existing native Agent/research selector are on the left;
voice and send icons are on the right. All existing modes and operations stay.
Voice keeps browser disclosure consent and text review before send.
Upload remains staged until Send. Active review and auth guards unchanged.
Text height resets after submission. No backend, provider or permission change.

Checks: `python -m pytest -q` (533); `python check_composer_browser.py`
(320/390/1280, light/dark; geometry,44px controls,staged file,voice stop,
Shift+Enter,mode request,one send,reset,external select wrapper).
Existing approval/status and private-export browser fixtures pass.

Design sources inspected October10: actual https://chatgpt.com/ composer;
Claude signed-out at https://claude.ai/login, public screenshot
https://media.aiuxplayground.com/images/gallery/claude/tool-switching/calm-default.webp
via https://aiuxplayground.com/teardowns/claude/composer.
Fresh UI code only, no third-party source/assets copied.

Independent exact-head review and owner release checkpoint required before ship.
