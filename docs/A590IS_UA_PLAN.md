# CHDK A590 IS Ukrainian Edition — development plan

Target camera: Canon PowerShot A590 IS, original firmware **GM1.01B**.
Target CHDK port: `platform/a590/sub/101b`.

## Safety and scope

- Keep `trunk` unchanged until a reviewed pull request is merged.
- Preserve the original Canon firmware; prefer reversible SD-card CHDK loading.
- Never deploy a build for firmware 1.00E to a 1.01B camera.
- Confirm reproducible baseline builds before editing camera-specific assembly or boot code.
- Test on physical hardware before claiming the build is safe or stable.

## Phase 0 — baseline

- [ ] Record upstream CHDK revision and license obligations.
- [ ] Identify the exact supported build instructions and ARM cross-compiler version.
- [ ] Build unmodified CHDK for `a590` firmware `101b`.
- [ ] Record build commands, tool versions, logs, output names, size, and checksum.
- [ ] Inspect existing language resources, font encoding, and available memory.
- [ ] Confirm camera boots, takes JPG and RAW photos, and exits CHDK normally.

## Phase 1 — Ukrainian language

- [ ] Inventory UI strings and existing localization infrastructure.
- [ ] Implement Ukrainian locale with a compatible Cyrillic font/encoding.
- [ ] Verify text widths and rendering on the A590 IS physical LCD.
- [ ] Keep translated strings within existing memory and UI limits.

## Phase 2 — UX / UI

- [ ] Map physical keys, ALT mode, menus, and screen dimensions.
- [ ] Prototype a simple quick-access screen for exposure, RAW, and bracketing.
- [ ] Avoid breaking standard Canon menu, shooting, and playback modes.

## Phase 3 — photographic algorithms

- [ ] Benchmark baseline exposure and existing scripting/RAW functions.
- [ ] Prototype exposure bracketing and highlight-protection logic.
- [ ] Compare output on identical test scenes before proposing low-level patches.

## Change acceptance

Each change must compile, document affected hardware behavior, include a rollback path, and pass on-camera tests before a release is published.

This document is project planning, not a claim that a custom firmware build has been produced or tested.
