# Campaign and artwork coverage

Full campaign acceptance is **not complete**. Archive coverage and playthrough
coverage are separate evidence. A scanned or restored texture does not prove
that the corresponding mission runs correctly.

## Current live exploration

The full-coverage pack session `private/hd-full-campaign/result.json` closes
normally with exit 0 after 1,188 seconds, including inspection/idle time. It
uses a copy of the WIP save and preserves the real source saves, all 54 fonts,
normal preferences and pack metadata. Its normal-paced boot input reaches the
sanctuary; subsequent owned-window keyboard input is recorded in `recorded.pad`.
Neither that full recording nor a matching PPSSPP campaign trace has passed
independent replay, so route/campaign acceptance remains false.

| Current-pack observation | Screenshot in that folder |
|---|---|
| Inner sanctuary dialogue; original Dolphstein portrait | `0002.png`, `0005.png` |
| Outer sanctuary and Time Rift effects | `0010.png`, `0017.png` |
| Time Rift exchange dialogue and menu | `0021.png`, `0024.png`, `0026.png` |
| Return to Porto Carillo | `0033.png`, `0034.png` |
| Town NPC conversation; original portrait | `0036.png` |
| Save confirmation and completed write on QA copy | `0049.png`, `0050.png` |
| Return to title, Continue and character selection | `0052.png`, `0053.png`, `0055.png` |
| Newly saved QA copy loaded back into town | `0058.png` |

The session loads 377 replacements and uploads 97 authored mip chains / 291
levels, all using replacement art, with zero load failures, skips, bad factors,
over-budget events, rejected chains or mip-upload failures. Interpreter
instructions, entries and dispatch misses are zero. The save/write/return-to-title/
Continue observation is within one process and one WIP version, not proof of a
fresh-process or Japanese/English cross-version round trip. No combat mission,
boss or later chapter is completed here. FPS acceptance remains for playtesting.

Four ad-hoc networking cleanup calls report actual unsupported errors
`0x80010086`: `sceNetAdhocTerm`, `sceNetAdhocMatchingDelete`,
`sceNetAdhocMatchingStop` and `sceNetAdhocMatchingTerm`. These have not been
replaced with success. The session exits normally, but multiplayer remains
unsupported by this evidence. The next campaign work is a recorded combat
mission followed by independent replay and a matching PPSSPP trace.

## Earlier exploration

`private/campaign-session-02/result.json` records a 2,455-second native session
using a copy of the existing WIP save. It closed normally with exit 0. Source
saves, fonts and normal preferences were unchanged. Guest-delivered input was
recorded to `recorded.pad`; it has not yet passed an independent replay or a
matching PPSSPP comparison. Paused time is included in the session duration,
so this is not a continuous-play or performance soak result.

| Checkpoint | Observation | Private screenshot |
|---|---|---|
| Continue/load | Existing level-5 chapter-1 character loaded | Session input and captures |
| Town NPC | English conversation displayed | `0031.png`, `0035.png` |
| Gather interaction | Clean Water pickup notification displayed | `0044.png` |
| Area transition | Entered Arade Sanctuary | `0055.png`, `0057.png` |
| Interior transition | Entered inner sanctuary | `0068.png` |
| Story NPC | Dolphstein dialogue displayed in English | `0068.png`, `0071.png`, `0074.png` |
| Untranslated label | Floating Dolphstein name remains Japanese | `0085.png` |

The session uploaded 81 authored mip chains / 243 levels with zero mip-upload
failures. No quests or bosses were completed, no in-game save round trip was
performed, and Japanese/English cross-version persistence was not established
by this session. Existing earlier save tests retain their narrower scope.

## Shortened traversal work

The first bounded attempt, `private/campaign-temple-short-02/`, exits 0 and has
zero mip/replacement failures, but its actual screenshot is the closed guild
door, not the intended sanctuary. It is a failed route checkpoint, not a temple
pass. Revised input in `private/campaign-temple-short-03.pad` reaches the outer
sanctuary foyer at vblank 8500–8510, with exit 0, 64 mip uploads / 192 levels
and zero upload/replacement failures. It records additional real material
captures for offline work. It does not prove entry into the inner room or any
quest/boss completion. All source saves, fonts and normal preferences stay
unchanged. Matching PPSSPP replay remains outstanding for this new route.

The later `private/campaign-temple-short-04/` reaches the inner doorway but not
the inner room. `private/campaign-temple-short-05.pad` extends that movement and
**does reach the inner room and Dolphstein's English dialogue** in the actual
8900–8910 native capture. It exits 0 with 82 mip uploads / 246 levels and zero
upload/replacement failures. The execution report records zero interpreter
instructions, interpreter entries and dispatch misses. 79 real material chains
/ 237 levels were captured with zero failed writes. Source saves, fonts,
preferences and default pack contents remained unchanged.

This is a bounded native checkpoint, not yet a matching PPSSPP replay, quest
completion or full campaign acceptance. For the software oracle, the pinned
debugger supports `input.analog.send` and `cpu.runUntilTime`; the button-only
headless press flag is insufficient for this analog movement route. A reference
runner must measure the vblank/time alignment rather than substitute wall time.

## Efficient acceptance route

Use archive-wide enumeration and content hashes to avoid restoring or reviewing
the same shared texture repeatedly. Keep all original references in the private
catalog. Batch processing can cover unseen artwork; it cannot certify unseen
gameplay. Repeated optional encounters can be sampled, with omissions recorded.

Prioritize distinct environments, enemy/material families, boss transitions,
cutscenes/subtitles, inventory/shops, quest rewards, notifications, save/load and
language switching. Each accepted route needs exact input/image/runtime pins,
copied-save provenance, replayable input, expected checkpoints, actual failures
and an independent reference where available. Do not mark an entire chapter
passed from a single room or a successful process exit.

`tools/campaign-session.py` accepts bounded command files only for its owned
game window. `--capture-mips` optionally records bounded private authored-mip
data for broader art work. It changes no guest code, PSP results or source save.
The harness never marks the campaign passed automatically.
