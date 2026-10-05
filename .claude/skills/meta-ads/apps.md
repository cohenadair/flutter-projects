# Apps

Running per-app settings for Meta ads. Update a row whenever we create or change
ads for that app. If a value needed for the current task is `?`, ask the user and
fill it in **before** creating anything.

| App | Languages | Countries | Ages / demographics | Meta app ID | App Store | Google Play | Assets folder |
|---|---|---|---|---|---|---|---|
| Activity Log | English | US, CA, GB, AU, NZ, IE | 18–65 (both platforms) | 1059232339882913 | id1458926666 | com.cohenadair.activitylog | `~/Downloads/activity-log-ads/` |
| Anglers' Log | English (app also supports Spanish) | US, CA, GB, AU, NZ, IE (Spanish markets MX, ES, AR, CL, CO once there are Spanish images) | 18–64 (hard limit; smartphone users) | 1100097140947439 | id959989008 | com.cohenadair.anglerslog | ? |
| Tapd | ? | ? | ? | ? | ? | ? | ? |

Store links: `https://apps.apple.com/app/<App Store ID>` and
`https://play.google.com/store/apps/details?id=<package>`.

## Notes

### Activity Log

- English-only app, so ads are English-only.
- Countries chosen by the user (2026-10) over worldwide: English-only app, and
  worldwide targeting at a small budget buys the cheapest installs, mostly from
  markets unlikely to become paying users.
- Asset folder layout: `Images/` (app-store, google-play, universal variants),
  `Video/` (`Meta/` has per-platform 4:5 and 9:16), `Copy/` (`.docx` copy docs
  with headlines, primary text, and guardrails).
- The draft campaigns "Activity Log (iOS)" / "(Android)" were discarded by the
  user on 2026-10-05; recreate them when the fixed 9:16 videos are ready.
  Creatives `1368056125401815` (iOS) and `1355275826679835` (Android) still
  exist and can be reused if the videos haven't changed.

### Anglers' Log

- Countries/ages chosen 2026-10-04: 18–64 as a hard limit (smartphone users),
  Fishing interest with Advantage+ detailed targeting. The app supports Spanish,
  but Spanish ads were dropped on 2026-10-05 because the ad images contain
  English text; only the English countries run until there are Spanish
  images.
- Legacy campaign "Anglers' Log" `6320243059585` (2019). Its link-click ad sets
  can't be switched to installs (legacy `smart_pse_enabled`), and it isn't
  SKAdNetwork-enabled, so Meta limits its iOS install ad sets to iOS ≤14.4.
  Being replaced by new, separate iOS (SKAdNetwork) and Android campaigns, then
  stopped.
- Legacy campaign copy: "Track, analyze, and share fishing catches and trips!" /
  "Customize Your Logbook" ("analyze" is US spelling, so fix it in new
  material). Images in the library: "iOS (1:1)" (iPhones) and "Android (1:1)"
  (Pixels).
- Minimum OS: iOS 15.6, Android 7.0 (API 24).
- New campaigns (2026-10-05, $10/day each): "Anglers' Log (iOS) – Installs"
  `52586620875189` (SKAdNetwork) and "Anglers' Log (Android) – Installs"
  `52586620889189`. Copy: "Never lose a great fishing spot again. Log every
  catch, map every spot and learn what really works. Free to download." /
  "Stop guessing. Start catching." Previews page:
  `~/Downloads/anglers-log-ad-previews.html`.
- Install measurement: neither app has the Meta SDK yet (only SKAdNetwork IDs
  in the iOS Info.plist), so Android installs aren't measured at all. Tracked
  in cohenadair/anglers-log#1163.
