# Apps

Running per-app settings for Meta ads. Update a row whenever we create or change
ads for that app. If a value needed for the current task is `?`, ask the user and
fill it in **before** creating anything.

| App | Languages | Countries | Ages / demographics | Meta app ID | App Store | Google Play | Assets folder |
|---|---|---|---|---|---|---|---|
| Activity Log | English | US, CA, GB, AU, NZ, IE | 18–65 (both platforms) | 1423092639929446 | id1458926666 | com.cohenadair.activitylog | ? |
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
- **SKAdNetwork-eligible since 2026-10-14.** Before that, the "Apple's
  SKAdNetwork Reporting" checkbox didn't appear for Activity Log, and the API
  rejected it with "App is Ineligible for Apple's SKAdNetwork" (3955033). After
  about a week of the new app version (Meta SDK on Android only; iOS is
  SKAdNetwork-only via `adair_install_attribution`) it became eligible without
  any change on our side.
- **iOS campaigns (2026-10-14):**
  - "Activity Log (iOS) - Installs (NEW)" `52588620593789`: the SKAdNetwork
    campaign, built from scratch in Ads Manager ($5/day). Published
    2026-10-14 after changing its objective to `OUTCOME_APP_PROMOTION` via the
    tool. Live creatives: Video `1129981892877832`, Carousel
    `1088411367440498`. Ad sets Video
    `52588620593989` and Carousel `52588621009789` (`campaign_attribution:
    SKADNETWORK`). Ads: Video `52588624034789` (duplicated in Ads Manager
    from `52588604263189`; 4:5 video `1654538436181709`, 9:16 video
    `2568809266877475` for Stories/Reels), Carousel `52588621290189` (copied
    with `source_ad_id`; creative `1668148758265736`, a newer copy of
    `1119157603778300`). Placements FB + IG + Threads; 6 countries; iOS 15.6+.
  - "Activity Log (iOS) – Installs" `52588604262989`: a duplicate of the
    original, with SKAdNetwork ticked at the campaign level, but its ad sets
    kept AEM (`attribution_setting: 1d_click`). Paused by the user; delete it.
  - "Activity Log (iOS) – Installs (OLD)" `52586847840589`: the original AEM
    campaign. Paused; delete it. AEM only gets data from the Meta SDK, which the
    iOS app doesn't have, so these AEM campaigns' installs were never measured.
- Old-app campaigns to delete: `52586731380989` (iOS), `52586731383789`
  (Android, paused).

### Anglers' Log

- Countries/ages chosen 2026-10-04: 18–64 as a hard limit (smartphone users),
  Fishing interest with Advantage+ detailed targeting. The app supports Spanish,
  but Spanish ads were dropped on 2026-10-05 because the ad images contain
  English text; only the English countries run until there are Spanish
  images.
- Legacy campaign "Anglers' Log (OG)" `6320243059585` (2019, paused; formerly
  named "Anglers' Log"). Its link-click ad sets
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
  "Stop guessing. Start catching."
- Install measurement: shipped in v2.8.1 (2026-10-07, commit `d59d7773`
  "#1163: Add Meta install attribution") through the
  `adair_install_attribution` plugin, with the Meta app ID and client token in
  the Android manifest. Android installs have shown in `results` since
  2026-10-07/08; iOS installs come through SKAdNetwork (late, and hidden at low
  volume). cohenadair/anglers-log#1163 is still open because it also covers
  Activity Log.
- Status (2026-10-13): new creatives are in progress. Until they arrive, don't
  recommend creative changes (e.g. Meta's 9:16 Reels video suggestion); the
  user is leaving both campaigns as they are for now.

### Tapd

- iOS bundle ID and Android package are both `com.cohenadair.colortap`
  (the app's original name was Color Tap). Minimum iOS: 15.6.
- Meta app ID is read on Android from
  `tapd/mobile/android/app/src/main/res/values/strings.xml`.
- Eligible for SKAdNetwork campaigns: "Apple's SKAdNetwork Reporting" appears
  when Tapd is picked in a new iOS 14+ campaign (checked 2026-10-07). Tick it
  when creating Tapd's iOS campaign; it can't be added later.
