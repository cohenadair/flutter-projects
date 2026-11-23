---
name: app-store-screenshots
description: >
  Designs App Store and Google Play marketing screenshots (captions, layouts,
  device frames, store banners, feature graphic) in the shared Next.js
  studio at `screenshots/studio`, and coaches the copy and visual design.
  Use when the user wants to design, restyle, re-caption, localize, or
  export marketing screenshots or store banners for one of this monorepo's
  apps, add a project to the studio, or change the studio itself. Triggers
  on app store screenshots, play store screenshots, marketing screenshots,
  screenshot studio, feature graphic, store banner, phone mockup. Capturing
  the raw device screenshots is `capture-store-screenshots`; uploading them
  to the stores is `store-release` Media mode.
---

# App Store & Google Play Screenshots Generator

## This monorepo: the shared studio

Every app here uses one hand-maintained editor, `screenshots/studio` (in
the `screenshots` repo). It started as this skill's template and has since
been customized heavily: multi-project, store banners, reskin-only
tenants, Mac decks, opaque Apple banners. **Read `screenshots/studio/README.md`
first**; it's the source of truth for how the studio works. Where it and
this skill disagree, the README wins, and this skill should be fixed.

- **Never scaffold or migrate here.** Don't copy `template/` into the
  studio or an app, and don't run [scaffold.md](scaffold.md)'s migration on
  the studio: it would overwrite the customizations. `scaffold.md` is only
  for a project outside this monorepo.
- **Run it:** from `screenshots/studio`, `pnpm dev`, then open the URL it
  prints and pick the project (`?project=<id>`). If a `next dev` is already
  running there, reuse it. Never run `next build` alongside it; check
  compile errors with `npx tsc --noEmit` (see
  `.claude/troubleshooting/tooling.md`).
- **Projects:** registered in `screenshots/studio/projects.json`
  (activity-log, anglers-log, pro-iq, tapd). Each project's data lives in
  *its own repo* at its `root` (e.g. `anglers-log/screenshots/assets/`):
  `app-store-screenshots.json` plus its screenshots. Add a project with one
  entry there; no code change.
- **Where this skill says** `public/screenshots/...` or "the project root",
  read the project's asset `root` instead. Screenshot paths in the project
  JSON are served through `/api/asset/<projectId>/...`.
- **Copy and layout changes** go through the editor, or by editing the
  project's `app-store-screenshots.json` with JSON tooling (never regex) while
  the dev server is stopped or after a reload, since the editor autosaves
  over it.
- **Raw screenshots** come from `capture-store-screenshots` (projects in
  `screenshots/capture/projects.json`), which writes straight into the
  project's asset folder.
- **Upload** exported screenshots and banners with `store-release` Media
  mode.
- **Changing the studio's code** is a change to the `screenshots` repo:
  commit there, not in the app repos. Commit a project's
  `app-store-screenshots.json` and assets in that app's repo.

## Core Principle

**Screenshots are advertisements, not documentation.** Every screenshot sells one idea. If you're showing UI, you're doing it wrong — you're selling a *feeling*, an *outcome*, or killing a *pain point*. Use this skill's interactive editor to iterate on copy and layout fast; do not hand-craft the page from scratch.

## Coach the User on Copy

Inside the editor the user will write headlines themselves, but they often need guidance. Apply these rules when reviewing their copy or generating suggestions.

### The Iron Rules

1. **One idea per headline.** Never join two things with "and."
2. **Short, common words.** 1-2 syllables. No jargon unless it's domain-specific.
3. **3-5 words per line.** Must be readable at thumbnail size in the App Store.
4. **Line breaks are intentional.** Newlines in the textarea map directly to visible breaks.

### Three Approaches

| Type | What it does | Example |
|------|-------------|---------|
| **Paint a moment** | You picture yourself doing it | "Check your coffee without opening the app." |
| **State an outcome** | What your life looks like after | "A home for every coffee you buy." |
| **Kill a pain** | Name a problem and destroy it | "Never waste a great bag of coffee." |

### Bad-to-Better

| Weak | Better | Why |
|------|--------|-----|
| Track habits and stay motivated | Keep your streak alive | one idea, faster to parse |
| Organize tasks with AI summaries | Turn notes into next steps | outcome-first, less jargon |
| Save recipes with tags and favorites | Find dinner fast | sells the benefit, not the UI |

### Narrative Arc

The user's slide deck should follow a rough arc (skip slots that don't fit):

| Slot | Purpose |
|------|---------|
| #1 | **Hero / Main Benefit** — the ONLY slide most people see |
| #2 | **Differentiator** — what makes the app unique |
| #3 | **Ecosystem** — widgets, watch, extensions (skip if N/A) |
| #4+ | **Core Features** — one per slide, most important first |
| 2nd-to-last | **Trust Signal** — "made for people who [X]" |
| Last | **More Features** — pills listing extras (skip if few features) |

### Layout Variation

Vary the `layout` field across slides. The editor exposes:
- `hero` — centered headline + bottom-anchored device
- `device-bottom` — same composition, smaller headline
- `device-top` — flipped, device above caption (good contrast slide)
- `two-devices` — back + front phones layered
- `no-device` — big standalone headline (use sparingly)
- `split-landscape` — caption left + device right (tablet landscape only)
- `feature-graphic` — Play Store banner (1024×500)

Never repeat the same layout twice in a row. Use 1-2 `inverted` (dark) slides for visual rhythm.

### Cross-Screen / Cross-Canvas Composition

Use the connected canvas as a design tool while coaching the copy, after the narrative arc and layout rhythm are chosen and before final export. For most decks with **5+ slides**, plan **one** tasteful cross-screen moment by default. For 8-10 slide decks, use at most **two**. For short, formal, or compliance-heavy decks, zero is fine. The goal is "these screenshots belong together," not "one giant poster chopped into pieces."

Good cross-screen patterns:
- An oversized phone, tablet, or screenshot mosaic bridges two adjacent screens by 10-30% of its width, while each exported crop still reads as a complete ad.
- A background horizon, photo, gradient, doodle path, waveform, starfield, sticker trail, or map route continues across the seam.
- A mascot, 3D object, floating chip, or notification peeks from one screen into the next as a secondary visual, not the whole message.
- Related ideas form a pair: problem → solution, before → after, overview → detail, plan → result.
- The seam passes through negative space, a soft shadow, a simple object body, or a non-critical decorative area.

Bad cross-screen patterns:
- Splitting headlines, app names, prices, legal text, ratings, CTAs, or critical UI across a seam.
- Centering one giant phone on the seam so each crop shows only a half-device and no clear benefit.
- Using cross-screen movement on every slide; it becomes a gimmick and makes the deck harder to scan.
- Cutting through faces, mascot eyes, key chart numbers, product claims, or app-store-required information.
- Requiring the viewer to understand the carousel as one uninterrupted poster. Every exported PNG must still pass the one-second standalone test.
- Letting shadows, stickers, or partial objects look accidentally clipped. If it crosses a boundary, make the bleed deliberate with scale, shadow, rotation, or continuation.

Placement rules:
- Use adjacent screens only unless a deliberate 3-screen panorama is the entire concept.
- Keep all text fully inside a single exported screen with safe margins.
- Let 10-30% of a non-critical visual cross the seam; go beyond 40% only for backgrounds, paths, or abstract decoration.
- If adjacent screens have different background colors, bridge them with a shared object, matching shadow direction, or a designed transition band.
- Review both views: the zoomed-out connected canvas must look cohesive, and each individual export must still sell one idea.

## Visual Design Principles

These rules are derived from studying the best app store screenshots in the wild (Superlist, Headspace, CRED, (Not Boring) Camera, Arc Search, Linktree, Gentler Streak, etc.). They apply regardless of which style preset the user picks. Style-specific tokens (fonts, palette, accents) live in `style-prompts.md` — point the user there.

### 1. The background is a designed surface — never white

Plain white is the amateur tell. Every great deck uses a deliberate surface: a saturated color block, a warm cream/off-white (`#F4F1EC`-ish), a dark navy/near-black, or a gradient. The background can shift per slide (Headspace, Linktree do this), but it must read as intentional, not default.

### 2. Headlines dominate

The headline occupies roughly the **top 30–40%** of the canvas — much bigger than a typical web hero. If a person can't read it at thumbnail size with no zoom, redesign.

### 3. Mixed emphasis inside the headline

Almost every great headline has one word styled differently from the rest — a contrast color, an italic script, a heavier weight, or a hand-drawn underline. Examples:
- Superlist: "The one app that fits **your whole day**" (script + coral)
- Headspace: "Stress **less**" (`less` orange against black)
- Arc Search: "**Fastest** way to search. **Cleanest** way to browse." (purple / navy)

Flat single-color headlines look weaker. Pick one emphasis word per slide.

### 4. Decorative accents are the rule, not the exception

Top decks layer at least one of these on most slides:
- Hand-drawn squiggles, arrows, scribbles (Superlist)
- Sparkles / glow (Gentler Streak, Arc)
- Label badges on the visual ("SUPER RAW", "Cinematic", "LUT")
- Floating widget chips with real stats ("$3,630 earned", "11,175 steps") — these tell the story without copy
- Award lockups on the hero only (Apple Design Award, Webby, star count)

A bare phone on a bare bg with a bare headline is the default-skill output. Add one accent.

### 5. Phone framing is a deliberate choice — vary it across the deck

Three common framings, each carries a different feeling:
- **Bezelless / minimal frame** — maximizes UI legibility, modern (Arc, Linktree, Gentler)
- **Tilted floating phone with soft shadow** — product / advertorial feel (Superlist, CRED hero)
- **Full device with visible bezel, dead-center** — editorial, premium (CRED, NB Camera)

Mix at least two framings across the deck.

### 6. Proof anchors the hero, nothing else

Award badges, press quotes, star counts, install counts — concentrate them on **slide 1 only**. Spreading them dilutes both the proof and the rest of the slides. NB Camera does this perfectly: Verge quote + Apple Design Award + 15,000+ stars all on the cover, none after.

### 7. Density inside the phone, sparsity outside

The screenshot inside the phone can (and should) be a real, dense product capture — actual lists, dashboards, charts, conversations. The space *outside* the phone is the opposite: one headline, one visual, one optional sub-line, one optional badge. Don't add bullet lists, multi-line paragraphs, or competing logos around the device.

### 8. Break the phone parade

Every 2–3 slides, drop the phone and use a different hero element to keep visual rhythm:
- 3D rendered product object (NB Camera's stylized camera)
- Photographic still (NB Camera slide 2)
- Real human / lifestyle photo (Linktree)
- Mascot illustration (Headspace's mascot, Gentler Streak's character)
- Typographic feature wall (Superlist's last slide)
- Phone grid mosaic (Linktree's "Trusted by 70M+" final slide)

### 9. Last slide pattern

The closer is almost always one of two things:
- **Feature wall** — a vertical list of one-word features styled as big type ("Real-time collaboration / Offline support / Widgets / Integrations…")
- **Phone mosaic** — multiple bezelless mini-screenshots arranged in a grid to convey "look at all the things this does"

Pick one. Don't make the last slide another single-feature hero — it wastes the spot.

### 10. Thumbnail test (mandatory before export)

Shrink the slide to ~160px wide (App Store search-result size). Squint. Can you read the headline? Can you tell what the app does in under a second? If not, the headline is too long, the type is too thin, or there's no contrast between text and background. Fix before exporting.

## Localization

**Always confirm the language list with the user** — even if they didn't volunteer it. In this monorepo, a project's locales usually match the app's supported locales; check the project JSON first. Ask: _"Should screenshots be localized? If yes, which locales? (e.g. en, de, es, pt, ja)."_ Default to English-only if they say no or skip.

The project state file (`app-store-screenshots.json`) carries a `locales: string[]` field — the list of locale codes the project targets. The editor reads this to decide:
- The locale dropdown in the toolbar is **hidden** when `locales.length <= 1`.
- The dropdown's options come from this list (not a hardcoded set).
- The **Export bundle** loops every locale in the list × every required size.

**Edit the project's `app-store-screenshots.json` to set `locales` to the user's chosen list, e.g.** `"locales": ["en", "de", "ja"]`. Also set `"locale": "en"` (or whichever is the source-of-truth language) so the editor opens on it.

The editor stores headlines and labels per-locale on each slide — switch to a locale and type to fill it in; unfilled locales fall back to `en` at preview time. Screenshots are a single string per slide; put `{locale}` anywhere in the path and the editor substitutes the active locale at render and export (e.g. `/screenshots/apple/iphone/{locale}/01.png`).

- Don't literally translate — rewrite for the target market.
- Re-check line breaks per locale; German/French/Portuguese often need shorter claims.
- For RTL (`ar`, `he`, `fa`, `ur`), the template handles direction inversion through CSS — let the user verify each slide looks intentional, not just flipped.

## Export

Inside the editor, the user picks a device, then hits **Export bundle**. A single zip downloads with every required size × every project locale for that device, organized as `<platform>/<device>/<WxH>/<locale>/NN-<layout>.png`. Repeat per device.

When `connectedCanvas` is enabled, exports are crops of the connected canvas, not isolated screen renders. If a mockup sits halfway across screen 2 and screen 3, screen 2's PNG contains its left crop and screen 3's PNG contains its right crop exactly as placed. Legacy decks should start with `connectedCanvas: false`, so old offscreen/clipped elements export as they did before. The user can turn on **Connected** after intentionally composing cross-screen elements.

Before export, zoom out to inspect the connected canvas as a strip, then inspect the individual cropped screens. Cross-screen elements should feel intentional in the strip and harmless in isolation.

Project locales come from the project JSON's `locales` field (see Localization). Single-locale projects produce a flat per-size structure with just the one locale folder.

If exports come out blank or with black screen rectangles:
- Verify source screenshots are RGB (not RGBA). The template flattens via `objectFit: cover`, but truly transparent sources can still produce black regions.
- Confirm the referenced screenshot paths exist under the project's asset `root`; export retries paths that were previously missing before it starts rendering.
- Keep export scaling inside `html-to-image` via `canvasWidth`/`canvasHeight`; CSS `transform: scale(...)` can leave transparent gutters when App Store sizes differ slightly in aspect ratio.

## Final QA Gate

### Message Quality
- One idea per slide
- Hero slide communicates the main benefit in one second
- Readable at arm's length at thumbnail size

### Visual Quality
- No two adjacent slides share the same layout
- Landscape tablet slides use `split-landscape` — never two devices side-by-side
- At least one contrast (`inverted: true`) slide when the deck is long enough
- For decks with 5+ slides, either one cross-screen/cross-canvas moment exists or there is a clear reason to keep every screen isolated
- Cross-screen moments are limited to adjacent screens and never split text, required info, faces, or critical UI

### Export Quality
- No clipped text or assets after scaling to export size
- No transparent gutters or blank edge pixels in the generated PNGs
- Cross-screen elements split cleanly across adjacent PNGs
- Screenshots correctly aligned inside every device frame
- Filenames sort correctly (zero-padded numeric prefixes)
- Feature Graphic exports cleanly at 1024×500 (no device frame)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Edited `page.tsx` instead of using the editor | Roll back the edit; let users iterate in the browser |
| Tried to rebuild device frames from scratch | They're in `src/components/editor/device-frames.tsx` — modify there |
| Left uploads uncommitted | Drop-target uploads are written to the project's asset folder (`<root>/screenshots/uploaded/<hash>.png` in the studio; `public/screenshots/uploaded/` in a scaffolded project). Commit them **and** `app-store-screenshots.json` in the app's repo so the deck reproduces after `git clone`. |
| Wrong directory layout for tablet screenshots | Match the layout the project's asset folder already uses (e.g. `android/tablet-7/portrait/{locale}/...`) |
| Reset wiped the deck | Reset clears in-memory state and re-saves defaults to `app-store-screenshots.json`. Recover by `git checkout app-store-screenshots.json` if it was committed, or export first before resetting. |
| Export is blank | Source PNGs probably have alpha — flatten to RGB |
| Dev server port collision | Let Next pick the next free port (3001+), and read the URL from its output |

