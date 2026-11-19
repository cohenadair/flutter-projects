# Apps

Running per-app settings for Meta ads. Update a row whenever we create or change
ads for that app. If a value needed for the current task is `?`, ask the user and
fill it in **before** creating anything.

| App | Languages | Countries | Ages / demographics | Meta app ID | App Store | Google Play | Assets folder |
|---|---|---|---|---|---|---|---|
| Activity Log | English | US, CA, GB, AU, NZ, IE | 18–65 (both platforms) | 1423092639929446 | id1458926666 | com.cohenadair.activitylog | ? |
| Anglers' Log | English (app also supports Spanish) | US, CA, GB, AU, NZ, IE (Spanish markets MX, ES, AR, CL, CO once there are Spanish images) | 18–64 (a suggestion: Advantage+ audience on since 2026-11-19) | 1100097140947439 | id959989008 | com.cohenadair.anglerslog | `~/Downloads/anglers-log-meta-ads` |
| Tapd | English | US, CA, GB, AU, NZ, IE | 18–65 (hard limit) | 906547471192431 | id1019522139 | com.cohenadair.colortap | `~/Downloads/tapd-campaign-videos` (cut videos in `ads/`) |

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
  placements): "Activity Log (Android)" `52586848618189` (originally
  "… – Installs") and the original iOS campaign `52586847840589` (since
  replaced; see below), each with a Video and a Carousel ad set (1 ad each).
  Copy: video "One tap. Real answers." / "Tap to
  start. Tap to stop. Track from your lock screen [Android: notifications] and
  get stats you'll actually use. Your data stays on your phone." / "Free to
  download"; carousel "Busy all week with nothing to show for it? Track
  workouts, hobbies and side projects in one tap and see where the hours go."
  Creatives: iOS video `2271107360412381`, iOS carousel `1119157603778300`,
  Android video `2229159977866258`, Android carousel `1763512701585473`.
  With the campaign budget, Meta gave the Android Video ad set almost
  nothing (0.04 CAD in Oct 20–26, 0.57 in Nov 3–9). **Merged 2026-11-10:**
  the video ad was copied into the Carousel ad set `52586848842589` as ad
  `52594319892189` (same creative, via `source_ad_id`), and the Video ad set
  `52586848840589` was paused. The Android ad sets target Facebook and
  Instagram only, no Threads (they predate the Threads default).
- **SKAdNetwork-eligible since 2026-10-14.** Before that, the "Apple's
  SKAdNetwork Reporting" checkbox didn't appear for Activity Log, and the API
  rejected it with "App is Ineligible for Apple's SKAdNetwork" (3955033). After
  about a week of the new app version (Meta SDK on Android only; iOS is
  SKAdNetwork-only via `adair_install_attribution`) it became eligible without
  any change on our side.
- **iOS campaigns (2026-10-14):**
  - "Activity Log (iOS)" `52588620593789` (originally "… - Installs (NEW)"):
    the SKAdNetwork campaign, built from scratch in Ads Manager ($5/day).
    Published
    2026-10-14 after changing its objective to `OUTCOME_APP_PROMOTION` via the
    tool. Live creatives: Video `1129981892877832`, Carousel
    `1088411367440498`. Ad sets Video
    `52588620593989` and Carousel `52588621009789` (`campaign_attribution:
    SKADNETWORK`). Ads: Video `52588624034789` (duplicated in Ads Manager
    from `52588604263189`; 4:5 video `1654538436181709`, 9:16 video
    `2568809266877475` for Stories/Reels), Carousel `52588621290189` (copied
    with `source_ad_id`; creative `1668148758265736`, a newer copy of
    `1119157603778300`). Placements FB + IG + Threads; 6 countries; iOS 15.6+.
    Until 2026-10-22 both ad sets also delivered to Audience Network (hidden
    under "spend on excluded placements"; ~a third of spend, accidental taps);
    the user unticked it on 2026-10-22, and Advantage+ audience was turned
    off the same day (18–65 is now a hard limit). Learning restarted
    2026-10-22. Confirmed in the 2026-10-27 status update: no Audience Network
    impressions after 2026-10-22, and `page_types` no longer lists
    `mobileexternal`. SKAdNetwork installs now show in `results` (3 in
    Oct 20–26, 2 of them credited to Audience Network impressions from before
    the fix), and keep reporting as numbers (1–2 a week), not "Not available".
    **2026-11-10:** Video ad set `52588620593989` paused (Oct 23–Nov 9: CAD
    37.83 for 1 install, CTR 0.44%, against the Carousel's 4 installs at CAD
    12.61), and the campaign budget lowered from $5 to $4/day, with the $1
    moved to Tapd (Android).
  - Deleted (gone from the account by 2026-10-20): AEM iOS campaigns
    `52588604262989` (a duplicate whose ad sets kept AEM) and `52586847840589`
    (the original). AEM only gets data from the Meta SDK, which the iOS app
    doesn't have, so their installs were never measured.
- Old-app campaigns `52586731380989` (iOS) and `52586731383789` (Android):
  deleted (gone from the account by 2026-10-20).
- **Paused 2026-11-19:** both campaigns ("Activity Log (iOS)"
  `52588620593789`, "Activity Log (Android)" `52586848618189`), on the
  user's call. Their $4 + $4 a day went to Tapd. In Nov 10–16 Android got
  1 install for CAD 34.95 and iOS 5 for CAD 28.71, against Tapd's 68 at
  about CAD 1.10. Their daily budgets are still set to $4 each, so turning
  them back on would put the account over the $30 cap unless other budgets
  come down first.

### Anglers' Log

- Countries/ages chosen 2026-10-04: 18–64 as a hard limit (smartphone users),
  Fishing interest with Advantage+ detailed targeting. **Since 2026-11-19
  Advantage+ audience is on** (user accepted Meta's recommendation), so
  18–64 and Fishing are suggestions. Only `age_min` 18 is a hard limit, and
  the API now reads back `age_max` 65 with `age_range` [18, 64]. The app supports Spanish,
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
  the user's $20/day account-wide cap): "Anglers' Log (iOS)"
  `52586620875189` (SKAdNetwork) and "Anglers' Log (Android)"
  `52586620889189` (both originally "… – Installs"). Copy: "Never lose a
  great fishing spot again. Log every catch, map every spot and learn what
  really works. Free to download." / "Stop guessing. Start catching."
- Install measurement: shipped in v2.8.1 (2026-10-07, commit `d59d7773`
  "#1163: Add Meta install attribution") through the
  `adair_install_attribution` plugin, with the Meta app ID and client token in
  the Android manifest. Android installs have shown in `results` since
  2026-10-07/08; iOS installs come through SKAdNetwork (late, and hidden at low
  volume). cohenadair/anglers-log#1163 (which also covered Activity Log) was
  closed on 2026-10-14.
- **Creative refresh (published 2026-10-27).** New marketing videos and
  carousels (not AI). Each campaign now has two ad sets, and Threads was added
  to the existing ones. The static "Stop guessing (free)" ads (iOS
  `52586622477989`, Android `52586622487989`) are paused.
  - iOS: "– Installs" ad set `52586620932789` (SKAdNetwork) with Carousel ad
    `52591152809789` (creative `1136952555514233`); "– Video" ad set
    `52591152570589` (SKAdNetwork) with Spot `52591152780989` (creative
    `2177334672994874`) and Bite `52591152790789` (creative
    `1393620549226090`).
  - Android: "– Installs" ad set `52586620965189` with Carousel ad
    `52591152811389` (creative `5139533152939836`); "– Video" ad set
    `52591152584189` with Spot `52591152803189` (creative
    `1146725914970346`) and Bite `52591152805389` (creative
    `4608780849367271`).
  - Carousel cards 4 and 6 say "(Pro)" because GPS trails and the species
    counter are Pro features. Card headlines truncate in Facebook Feed.
  - Spanish App Store previews are still pending from marketing.
  - In Nov 3–9, Meta gave the "Bite" ads almost no budget in both Video ad
    sets (CAD 0.17 Android, 3.80 iOS) and put nearly all of it into "Spot"
    (the best Anglers' Log ad: Android 8 installs at CAD 3.18). Same again
    in Nov 10–16 (CAD 0.22 Android, 0.48 iOS).
  - Meta has since rewritten the Carousel creatives: the live ones are iOS
    `1837549557682013` and Android `2978537462493735` (seen 2026-11-19).
- **Ad sets merged 2026-11-19** (Meta's "fragmentation" recommendation;
  the user dropped the 2-ads-per-ad-set rule the same day). Each campaign
  now runs one ad set, the "– Video" one, with three ads: Spot, Bite and
  Carousel.
  - The Carousel ads were copied in with `source_ad_id`: iOS
    `52596597234589` (into `52591152570589`) and Android `52596597211989`
    (into `52591152584189`).
  - The "– Installs" ad sets (iOS `52586620932789`, Android
    `52586620965189`) are paused.
  - Both Video ad sets have Advantage+ audience on, and their learning
    restarted on 2026-11-19.
  - This also cleared Meta's "add a 9:16 Reels video" recommendations,
    which were only for the carousel-only Installs ad sets. Spot and Bite
    already have 9:16 versions (`placement_videos`).

### Tapd

- iOS bundle ID and Android package are both `com.cohenadair.colortap`
  (the app's original name was Color Tap). Minimum iOS: 15.6.
- Meta app ID is read on Android from
  `tapd/mobile/android/app/src/main/res/values/strings.xml`.
- Eligible for SKAdNetwork campaigns: "Apple's SKAdNetwork Reporting" appears
  when Tapd is picked in a new iOS 14+ campaign (checked 2026-10-07). Tick it
  when creating Tapd's iOS campaign; it can't be added later.
- Minimum Android: 7.0 (`minSdk` is Flutter's default).
- Structure (2026-10-30): one campaign per platform with a **single ad set**
  each, $5/day at launch. Placements are the defaults **plus Messenger** (Tapd only).
- Approved copy (2026-10-30):
  - Primary text: "Tap the matching targets as fast as you can. Then watch
    out: the target changes! Take it slow on Very Easy or test your reflexes
    on Expert."
  - Headline: "Tap faster than you can think"
  - Description: "Free to play, always"
  - CTA: "Play Game" (`PLAY_GAME`); Meta accepts it for app installs.
- Campaigns (published 2026-10-30, CAD 5/day each; Android raised to 6/day
  on 2026-11-10 with $1 from Activity Log iOS, after CAD 1.09 per install in
  Nov 3–9; iOS raised to 6/day on 2026-11-19 with $1 from Activity Log
  Android). **Both at $10/day since 2026-11-19**, after Activity Log was
  paused and its $8/day was split evenly. That's a jump of about 67% each,
  so expect learning to restart. Meta still marks both as budget-limited. Messenger positions
  `messenger_home` and `story` were accepted, but **Meta doesn't deliver
  there**: both ad sets list `messenger` in `publisher_platforms` but not in
  `effective_publisher_platforms`, and the Oct 27 – Nov 2 breakdown had no
  Messenger rows (checked 2026-11-03).
  - iOS: campaign `52591843605589` (SKAdNetwork), ad set `52591843623389`,
    ad `52591846070989`, creative `1440615194341089`.
  - Android: campaign `52591843631389`, ad set `52591843638789`, ad
    `52591846080189`, creative `1663866981931055`.
  - Videos: 4:5 `2241089453128653` (fallback), 9:16 `1119899097086286`
    (Stories/Reels, including Messenger Stories).
- Videos: not AI-generated. **One set for both platforms**
  (`ads/tapd_9x16.mp4`, `ads/tapd_4x5.mp4`): the phone frame is generic and
  the status bar is cropped, so nothing in them is iOS- or Android-specific.
  Cut from the raw iPhone simulator preview with the full gameplay in a 30px
  black phone frame on the icon's dark purple (`#1E0336`); a two-line "Tap
  the matching / targets as they fall" hook over the first frame, frozen for
  1.5s so it can be read; and an end card (icon,
  "Tapd", "Play for free, always") on `#333333`. The app icon artwork has
  compression noise baked into its background; denoise it (`ffmpeg -vf
  nlmeans=s=6:p=7:r=21`) before showing it large. The iPad recording isn't
  used yet.
