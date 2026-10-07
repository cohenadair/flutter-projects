# Apps

Running per-app settings for Meta ads. Update a row whenever we create or change
ads for that app. If a value needed for the current task is `?`, ask the user and
fill it in **before** creating anything.

| App | Languages | Countries | Ages / demographics | Meta app ID | App Store | Google Play | Assets folder |
|---|---|---|---|---|---|---|---|
| Activity Log | English | US, CA, GB, AU, NZ, IE | 18–65 (both platforms) | 1423092639929446 | id1458926666 | com.cohenadair.activitylog | `~/Downloads/activity-log-ads/` |
| Anglers' Log | English (app also supports Spanish) | US, CA, GB, AU, NZ, IE (Spanish markets MX, ES, AR, CL, CO once there are Spanish images) | 18–64 (hard limit; smartphone users) | 1100097140947439 | id959989008 | com.cohenadair.anglerslog | ? |
| Tapd | ? | ? | ? | 906547471192431 | id1019522139 | com.cohenadair.colortap | ? |

Store links: `https://apps.apple.com/app/<App Store ID>` and
`https://play.google.com/store/apps/details?id=<package>`.

## Notes

### Activity Log

- English-only app, so ads are English-only.
- Countries chosen by the user (2026-10) over worldwide: English-only app, and
  worldwide targeting at a small budget buys the cheapest installs, mostly from
  markets unlikely to become paying users.
- Asset folder layout: current assets are in `01 Creatives/ActivityLog_Final/`
  (`Images/` per store, `Videos/Meta/<platform>/` 4:5 and 9:16,
  `Images_meta_v2/` = the carousel images actually uploaded). Copy docs
  (`.docx`) are in `02 Copy and briefs/`. The older `01 Creatives/Images/` and
  `Video/` folders are superseded.
- Minimum OS: iOS 15.6, Android 7.0 (API 24). Bundle ID and Android package
  are both `com.cohenadair.activitylog`.
- Meta app: the original app `1059232339882913` was deleted on 2026-10-06 and
  replaced by `1423092639929446` (no app type field; the old "Business" type
  isn't offered for new apps). Android reads the app ID and client token from
  `mobile/android/app/src/main/res/values/strings.xml`.
- Campaigns (2026-10-06, $5/day each, campaign budget, manual FB + IG
  placements): "Activity Log (Android) – Installs" `52586848618189` and
  "Activity Log (iOS) – Installs" `52586847840589`, each with a Video and a
  Carousel ad set (1 ad each). Copy: video "One tap. Real answers." / "Tap to
  start. Tap to stop. Track from your lock screen [Android: notifications] and
  get stats you'll actually use. Your data stays on your phone." / "Free to
  download"; carousel "Busy all week with nothing to show for it? Track
  workouts, hobbies and side projects in one tap and see where the hours go."
  Creatives: iOS video `2271107360412381`, iOS carousel `1119157603778300`,
  Android video `2229159977866258`, Android carousel `1763512701585473`.
- **Not yet eligible for SKAdNetwork campaigns (2026-10-07).** When Activity
  Log is picked in a new iOS 14+ campaign, the "Apple's SKAdNetwork Reporting"
  checkbox doesn't appear. It does appear for Anglers' Log and Tapd, which use
  the same SKAdNetwork-only iOS setup (`adair_install_attribution` plugin, no
  Meta SDK on iOS, Meta's SKAN IDs in Info.plist since v2.0.3), so it isn't a
  code problem. The API rejection is "App is Ineligible for Apple's
  SKAdNetwork" (3955033), on both the old and new Meta app. Meta's in-product
  AI says the app is likely below an install threshold and to release the new
  version and wait; no threshold is documented in Meta's help center.
  - Plan: release as planned, then recheck the checkbox every week or two by
    starting a new campaign draft. Once it appears, create a new iOS campaign
    with SKAdNetwork Reporting ticked (it can't be added to an existing
    campaign) and delete the AEM one. If it hasn't appeared after about a
    month, ask Meta support, citing Anglers' Log and Tapd as eligible.
  - Android installs (Meta SDK) are likely what counts toward the threshold;
    the iOS app sends Meta nothing.
- **Current iOS campaign uses AEM, not SKAdNetwork.** "Activity Log (iOS) –
  Installs" is an iOS 14+ campaign without SKAdNetwork Reporting, so it relies
  on Aggregated Event Measurement, which only gets data from the Meta SDK. Its
  installs aren't measured or optimized. The user chose to keep it running
  anyway (2026-10-07); don't pause it without asking. Edits fail with "No Opt
  Out Data … set up the Facebook SDK for iOS" (3955014). Its ad sets still have
  Advantage+ audience on (18–65 is a suggestion, not a hard limit).
- Old-app campaigns to delete: `52586731380989` (iOS), `52586731383789`
  (Android, paused).

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
- New campaigns (2026-10-05, $10/day each; lowered to $5/day on 2026-10-06 for
  the user's $20/day account-wide cap): "Anglers' Log (iOS) – Installs"
  `52586620875189` (SKAdNetwork) and "Anglers' Log (Android) – Installs"
  `52586620889189`. Copy: "Never lose a great fishing spot again. Log every
  catch, map every spot and learn what really works. Free to download." /
  "Stop guessing. Start catching." Previews page:
  `~/Downloads/anglers-log-ad-previews.html`.
- Install measurement: neither app has the Meta SDK yet (only SKAdNetwork IDs
  in the iOS Info.plist), so Android installs aren't measured at all. Tracked
  in cohenadair/anglers-log#1163.

### Tapd

- iOS bundle ID and Android package are both `com.cohenadair.colortap`
  (the app's original name was Color Tap). Minimum iOS: 15.6.
- Meta app ID is read on Android from
  `tapd/mobile/android/app/src/main/res/values/strings.xml`.
- Eligible for SKAdNetwork campaigns: "Apple's SKAdNetwork Reporting" appears
  when Tapd is picked in a new iOS 14+ campaign (checked 2026-10-07). Tick it
  when creating Tapd's iOS campaign; it can't be added later.
