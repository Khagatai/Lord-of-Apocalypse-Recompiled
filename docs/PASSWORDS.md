# English password entry

From beta.8, **Main Menu > Password** accepts the English aliases listed in
[config/Passwords.txt](../config/Passwords.txt). Type the alias into the native
keyboard and confirm. ASCII and full-width Latin are accepted without case
sensitivity. Extra spaces, punctuation, partial matches and unknown aliases
follow the normal game validation path.
Use Tab or the on-screen OK to confirm typed input; a controller uses Start.
Dismiss the unlock message and choose **Yes** at **Save your progress?** to keep
the reward after restarting. The original save confirmation is retained.

The original v1.6 patch's password MES resource retains Japanese matching keys.
The WIP translation preserves those keys too. The game uses the PSP OSK utility
for input, then converts a local MES record through its glyph table and compares
the result with the entered Unicode string. Translating display notifications
alone cannot make those Japanese keys enterable on a Latin keyboard.

The title extension expands a recognized alias immediately before the measured
password input length/count boundary at `08c9f6bc` in `08c9f680`. It reads the
original key from the current player's live MES and glyph table, validates all
spans and the complete single-line record, then writes only the 64-byte input
field. Original comparison, reward, duplicate, eligibility and save logic runs
afterwards. No success flag or reward is fabricated. Unknown inputs and malformed
resources are left untouched. Original Japanese codes still work.

The 13 aliases cover the 13 distinct keys referenced by the retail reward table
(message indices 0–9 and 20–22). Its unused message 23 is not an unlock code.
The table has two entries referencing key 22; their original game handling is
preserved. This update includes no retail password strings or copied patch
assets. Neither the original ISO nor the WIP archives need changing.

The pinned PPSSPP interpreter accepted the original key corresponding to VJump
and selected reward-table entry 5. Native checks confirmed the same quest unlock
at 30 and 60 FPS, the original incorrect-code notification, and a successful
save/restart/duplicate-entry round trip. A separate native run supplied SDL text
events and the keyboard's Tab confirmation through the visible OSK, without
scripted HLE answers. The compiled extension also reproduced all 13 original
keys from captured interpreter memory for ASCII and full-width inputs.

The private evidence is `private/beta8-review/`. All 449 project tests passed.
The full promotional quest/reward campaign and physical keyboard/controller
hardware matrix remain separate acceptance work. Native route tests use dummy
host audio, deterministic guest time and isolated saves. Some first attempts
hit wall-clock limits; successful repeat checks include unpaced presentation.

```powershell
./private/tools/python314/python.exe -m unittest discover -s tests -p test_password_alias.py
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
```

Optional local diagnostics: `LOA_PASSWORD_TRACE=1` reports only the selected MES
index and expanded length. No game files or raw passwords are uploaded.
