---
name: capture-store-screenshots
description: >
  Captures fresh App Store / Google Play screenshots on iOS simulators
  (iPhone, iPad) and Android emulators (phone, tablet), in every locale, from
  seeded data, using the shared `screenshots/capture` tool, and saves them
  into the project's screenshots studio assets so the new captures appear
  there automatically. Also keeps a project's seed translations in sync with
  its English seed. Use when the user says things like "update the
  anglers-log screenshots", "capture store screenshots", "retake the
  screenshots", "regenerate the iPad screenshots", "recapture 04 on
  Android", or edits seed data and wants new screenshots. Works for any
  project registered in `screenshots/capture/projects.json` (currently
  Anglers' Log).
---

# Capture store screenshots

The tool lives in `screenshots/capture/`, next to the studio in the
`screenshots` repo. Each project's configuration lives in that project (for
Anglers' Log, `anglers-log/screenshots/capture/`). Read both READMEs
first; they document how a run works, `capture.json`, the seed format, and
the screen catalog. Don't restate them to the user.

Never edit the app's code to make a screenshot work. Change the seed,
`capture.json`, or the project's capture entrypoint instead. If a screenshot
shows a real app bug, report it to the user.

## 1. Work out the scope

From the request, decide:

- **Project**: an id from `screenshots/capture/projects.json`.
- **Devices**: names from the project's `capture.json` → `devices`
  (default: all).
- **Locales**: from `capture.json` → `locales` (default: all).
- **Files**: specific file names like `04` (default: all).

If the user wants a different screen in a slot, or a new slot, update
`capture.json` → `captures` (and `screens` for a new screen/parameter
combination). A screen type that doesn't exist yet needs a new `case` in the
project's entrypoint (`show()`). Navigate by pushing routes or calling
callbacks rather than tapping, so no touch indicators are drawn.

## 2. Validate the seed

Run the project's seed check (Anglers' Log, from its capture folder:
`dart run build_seed.dart --check`).

- **Missing translations**: the user edits the English seed, so new or
  changed strings show up here. Add a real translation for each one to every
  file in `seed/translations/` (use correct domain terms; keep proper nouns
  such as person names, and names shown on the map, as-is). Remove entries
  whose English string no longer exists. Re-run until nothing is missing.
- **Missing photos**: stop and tell the user which files are missing. Only
  continue with placeholders (`-- --placeholder-photos`) if they say so.
- **Invalid seed**: fix the seed JSON (usually a misspelled proto field
  name), or ask the user if the intent is unclear.

## 3. Capture

From `screenshots/capture/`, run in the background (a full run builds the
app once per device and locale and takes a while):

```bash
dart run bin/capture.dart <project> --devices <...> --locales <...> --only <...>
```

Omit any option that should use its default; add `-- --placeholder-photos`
only if agreed in step 2. If the user has a `flutter run` session on one of
the devices, ask them to stop it rather than killing it.

The tool boots the simulators and emulators it needs and shuts down the ones
it booted. It only publishes a device's screenshots once all of that
device's locales succeed.

## 4. Check the results

The tool prints each published folder. Look at every new screenshot
(downscale into the scratchpad first, e.g. `magick 0*.png -resize x500
+append sheet.png`) and check for:

- Wrong or untranslated text in a translated screenshot (fix the seed
  translation, or report an app translation bug; don't fix app strings here).
- Text that wraps or truncates badly in another language (shorten the seed
  translation).
- Missing map tiles or images, or a spinner (raise that screen's
  `delaySeconds`).
- System dialogs, touch indicators, or an unexpected status bar.

Re-run just the affected files with `--only`. If a run fails, read the log it
names (in the app's `build/screenshots-capture/logs/`).

## 5. Report

Tell the user which files were updated per device and locale, and anything
you couldn't fix. Remind them to open the studio (`screenshots/studio`),
where the new captures already appear. Don't commit unless asked.
