---
name: meta-ads
description: >
  Manage the user's Meta (Facebook/Instagram) ad campaigns via the Meta Ads
  MCP server (`ads_*` tools) — listing campaigns and performance, and setting
  up app-install campaigns, ad sets, creatives, and previews for the user's
  apps (Activity Log, Anglers' Log, Tapd, and others). Defaults to the Cohen
  Adair Apps ad account (14363318); other accounts are only included when the
  user explicitly asks for all accounts. Use when the user says things like
  "show my campaigns", "check my Meta ads", "Facebook ads", "Instagram ads",
  "ad spend", "set up ads for <app>", "preview the ads", or names an app's
  campaign (e.g. "the Anglers' Log campaign"). Use Status Update mode
  (performance summary + recommendations) when they say "status update",
  "how are my ads doing", "campaign performance", "how can I improve my
  ads", "make my ads more efficient", or similar. Use the all-accounts
  summary when they say "all my accounts", "every account", "all my
  campaigns across accounts", or similar.
---

# Meta Ads

Manages campaigns through the Meta Ads MCP server. Its tools are deferred;
load them with `ToolSearch` (`select:mcp__<server>__ads_get_ad_accounts,...`
or a keyword search such as `+ads get_ad_entities`) before calling them.

Supporting files (next to this file):
- [`apps.md`](apps.md) — **per-app settings**: languages, target countries,
  ages, Meta app IDs, store IDs, asset folders. Read it before any work on an
  app's ads.
- [`reference.md`](reference.md) — ad accounts, business portfolios, Pages,
  Instagram accounts.
- [`scripts/frame_grid.swift`](scripts/frame_grid.swift) — video frame
  contact sheet for reviewing ad videos.
- [`scripts/preview_page.py`](scripts/preview_page.py) — one HTML page of all
  placement previews.

## Account scope

**Default account: Cohen Adair Apps — `14363318` (CAD).** Every request is
scoped to this account unless the user explicitly asks about all accounts.
Don't call `ads_get_ad_accounts` for normal requests — the ID is already
known. Don't mention or list the other accounts (see `reference.md`) in
default-scope answers.

### All-accounts summary

Only when the user asks about *all* accounts/campaigns:

1. Call `ads_get_ad_accounts` (follow `next_cursor` if present) — don't rely
   on `reference.md`, which may be stale.
2. For every account with `is_queryable: true` and `is_ads_mcp_enabled:
   true`, call `ads_get_ad_entities` with `level: "campaign"`, plus the
   `object_state: "draft"` call (see **Drafts** below), all in parallel.
3. For non-queryable accounts, list them with their `account_status` and
   `not_queryable_reason` instead of querying them.
4. Present one table per account (Cohen Adair Apps first), followed by the
   non-queryable accounts.

## Preferences

### Per-app settings

Targeting (languages, countries, ages/demographics) differs per app and lives
in `apps.md`. If a value needed for the task is missing (`?`), ask the user and
add it to `apps.md` before creating anything. Never assume one app's targeting
applies to another.

### Campaign structure (all apps)

- **One campaign per platform** (iOS / Android). Creative, copy, and store
  wording are platform-specific — never mix platforms in one ad.
- At small budgets (~$5/day per campaign), **at most 2 ads per ad set** so
  the budget isn't split too thin for Meta to learn.
- Goal: **maximize installs** (optimize for `APP_INSTALLS`). Don't try to
  link installs to subscribers or suggest subscription optimization unless
  the user asks.

### Copy (all apps)

- Use spelling common to **all regions** of each targeted language — no
  US-only English spellings; neutral Spanish for Spanish.
- **No dollar amounts** other than "free". "Free to download" is fine.
- Take copy from the app's `Copy/` docs (in its assets folder) and follow
  their guardrails (e.g. no cloud/sync claims, no star ratings, no invented
  stats). Read `.docx` files with `textutil -convert txt -stdout <file>`.
- **Confirm all copy with the user before going live** — primary text,
  headline, description, and CTA, per platform.

### Creative review (before using any asset)

- Videos: run `scripts/frame_grid.swift` and inspect every frame for
  platform-specific mistakes — wrong store badge or wording, iOS UI in an
  Android ad (or vice versa), on-screen content that contradicts itself
  (e.g. one activity started, a different one shown running).
- 9:16 videos: check safe zones (see **Video creatives** below).
- Ask about the AI disclosure for each new batch of assets — it can't be
  changed after the creative is created. Activity Log assets: not AI.
- Always offer previews before publishing.

## Calling the MCP tools

- **`client_conversation_id`** — required on every call. Generate one random
  20-character alphanumeric ID per conversation and reuse it for every Meta
  Ads call in that conversation.
- **`client_model`** — pass the exact model ID from the system context.
- **`advertiser_request`** — the user's own words, quoted verbatim.
- **`next_actions`** — if `ads_get_ad_entities` returns it, run every
  `read_only: true` action (without `requires_user_confirmation`) in `step`
  order before answering. Never run one that requires confirmation; propose
  it to the user instead.
- **Fields** — with no `fields`, `ads_get_ad_entities` returns only `id`,
  `name`, and `amount_spent`. Before requesting any other field (status,
  budget, results, etc.), verify its canonical name with
  `ads_get_field_context`.
- **Time range** — metrics default to the last 28 days. State the window in
  the answer, and pass `date_preset` / `time_range` when the user names one.
- **Drafts** — `ads_get_ad_entities` returns only published (`live`)
  objects by default. Unpublished Ads Manager drafts need a separate call
  with `object_state: "draft"`; it returns `ad_drafts` (campaigns, ad sets,
  and ads together, linked by `parent_ad_object_id`) instead of
  `ad_entities`, with no metrics. Whenever listing campaigns, make both
  calls (in parallel) so drafts aren't silently missed.
- **Budgets** are in cents of the account currency (`500` = $5.00).

## Setting up app-install campaigns

### Media

- The user uploads images/videos in Ads Manager (to the Cohen Adair Apps ad
  account). The upload tool's `LOCAL_FILE` mode doesn't work in this client.
- Find uploads with `ads_get_ad_videos` (`title` filter) or
  `ads_get_ad_images` (`name` filter), then fetch by ID and confirm
  `video_status: ready` before using them. If nothing's found, the user may
  have uploaded to another account or portfolio.

### Ad sets

- `promoted_object` needs the app's **Meta app ID** plus the store URL
  (`apps.md`). iOS install ads require the app ID; include it for Android too.
- `user_os` must match the app's **minimum supported OS** (see `apps.md`; verify
  against `IPHONEOS_DEPLOYMENT_TARGET` in `ios/Runner.xcodeproj/project.pbxproj`
  and `minSdk`, which is Flutter's default of API 24 / Android 7.0 when it's set to
  `flutter.minSdkVersion`). E.g. `iOS_ver_15.6_and_above`,
  `Android_ver_7.0_and_above`. `user_device`: iPhone/iPad/iPod or
  Android_Smartphone/Android_Tablet.
- iOS install campaigns on iOS 14.5+ need a **new campaign** with
  `is_skadnetwork_attribution: true`, a campaign-level `promoted_object` (app ID +
  App Store URL), and ad set `campaign_attribution: "SKADNETWORK"` (not `SKAN`).
  In a legacy campaign without it, Meta quietly limits iOS install ad sets to
  iOS ≤14.4.
- Countries and ages from `apps.md`. With Advantage+ audience on, ages are
  suggestions; set `targeting_automation.advantage_audience: 0` for a hard
  limit.
- Placements: Advantage+ (automatic) by default, unless `apps.md` or the user
  says otherwise. For manual Facebook + Instagram placements, don't include
  retired positions: Facebook `video_feeds`, Instagram `explore` (keep
  `explore_home`). Don't send `targeting_optimization`, which has been
  removed; Advantage+ detailed targeting now applies automatically.
- **Ad transparency (EU/DSA):** set `dsa_beneficiary` and `dsa_payor` to the
  value in `reference.md`. Meta otherwise defaults to the business name, which
  the user had to fix by hand.
- Spanish (or other non-English) ads: an ad set targets countries, not
  languages, so split ad sets by language and country group, each running
  ads in that language.

### Video creatives

- Use `placement_videos`: the **4:5** video as the fallback, the **9:16**
  video for `facebook_positions: [story, facebook_reels]` and
  `instagram_positions: [story, reels]`. No thumbnail is needed in this mode.
- **Always pass `instagram_user_id`** (`reference.md`). Without it the ad
  **won't deliver on Instagram**, even though Instagram previews still render.
- Pass `page_id` for the app's Page and `call_to_action_type:
  INSTALL_MOBILE_APP` with the store URL as `link_url`.
- **9:16 safe zones:** Reels/Stories crop ~5% off each side on tall phones,
  and the CTA/caption overlay covers roughly the bottom third. Key content
  should stay out of the outer ~6% on each side and the bottom ~35% (and the
  top ~14%).
- **Creatives are immutable.** Changing one means creating a new creative.
  `ads_creative_delete` isn't rolled out to this account yet, so ask the user
  to delete orphaned creatives in Ads Manager → Creatives.

### Previews

- Previews need an existing creative or ad. Creating a creative just for
  previews is low-risk (it can't run on its own) but still needs the user's
  OK.
- `ads_get_ad_preview` sometimes returns all placements and sometimes only
  the requested one — request each `ad_format` you need (Facebook Feed/Reels,
  Instagram Feed/Reels/Stories, Messenger Stories, Threads).
- Preview links expire (hours to a day or so). For a single page of all
  placements, write the URLs to a JSON file and run
  `scripts/preview_page.py`; save the HTML in the app's assets folder. It's
  for same-day viewing. For longer-lived sharing, use an Ads Manager share
  link (needs the ads created as drafts) or give the person Analyst access
  to the ad account.

### Publishing

- `ads_create_ad` / `ads_create_ad_set` stage objects in the Ads Manager
  draft — nothing goes live until it's published.
- Publish with `ads_activate_entity`, passing every draft campaign/ad set/ad
  ID in `object_ids`. A `PUBLISHING` result means handed off to Meta, not
  live — re-check the drafts or Ads Manager a few minutes later.

### Troubleshooting

- **Edits to live objects are staged as drafts** (`is_draft: true`) and need
  publishing with `ads_activate_entity`. A staged draft that fails validation
  **blocks every change underneath it** (e.g. pausing its ads). Fixing it with
  more draft edits rarely works; ask the user to **Discard drafts** on that
  object in Ads Manager.
- **Old link-click ad sets can't be switched to installs:** their promoted
  object carries a legacy `smart_pse_enabled` setting that `APP_INSTALLS`
  rejects. Instead, create a new install-optimized ad set in the same campaign,
  copy the ad with `source_ad_id`, publish it, then pause the old ads/ad set.
  When replacing an ad set, give the new one the old one's budget so total
  spend doesn't change, and verify budgets afterwards.
- **Meta reports validation errors one at a time.** Expect a few rounds of
  fixing when creating ad sets.
- **Older template/asset-feed creatives** (`{{product.name}}`) don't expose
  their text or image through `ads_get_creatives`. Read the text from a
  preview, and match the image through `thumbnail_url` against the image
  library's `url`.
- **Instagram account not visible** (`ads_get_ig_accounts` returns `[]`):
  1. In Business Settings → Instagram accounts → the account → **Connected
     assets**, make sure the ad account is added.
  2. If it shows in Ads Manager but not here, the connector lacks Instagram
     permission: remove the integration and reconnect the Meta Ads connector,
     granting "all and future" access.
- **Portfolios can't be merged.** Move individual assets (Instagram accounts,
  Pages) between portfolios instead; ad accounts can't be moved.

## Status Update mode

A performance summary of every campaign in the default account plus ranked
recommendations to make them **more efficient** (same results for less money)
and **more effective** (more installs). Read-only: never
apply a recommendation without the user's explicit "yes" (see **Changes**).

### Window

Default: **last 7 days**, compared with the **previous 7 days** (pass both as
`time_range`), plus lifetime totals for context. Use the user's window if they
name one.

### Step 1 — Gather (parallel where possible)

1. `ads_get_ad_entities`, `level: "campaign"`, with these verified fields:
   `name`, `effective_status`, `objective`, `daily_budget`, `amount_spent`,
   `results`, `cost_per_result`, `impressions`, `reach`, `frequency`, `ctr`,
   `cpm`, `cpc` — once per window. Follow any `next_actions` before moving on.
   Also make the `object_state: "draft"` call so unpublished work is listed.
2. Same fields at `level: "ad"` for campaigns that delivered, to compare
   creatives within each ad set.
3. **Setup check** at `level: "adset"`: `optimization_goal`, `targeting`,
   `promoted_object`, `destination_type`, `learning_stage_info`, and
   `daily_budget`. Plus breakdowns of the campaign by `publisher_platform` and
   by `country`. A wrong performance goal (e.g. `LINK_CLICKS` on an install
   campaign), worldwide targeting, or one placement eating the budget are the
   biggest problems, and **Meta's Opportunity Score and anomaly tools don't flag
   them**. Compare countries with the app's row in `apps.md`. A country
   breakdown can exceed the response limit; when it's saved to a file,
   summarize it with `jq` (top spenders, plus the share going to target
   countries).
4. Account-level signals (scope with `entity_ids` where useful):
   `ads_insights_anomaly_signal`, `ads_get_opportunity_score`,
   `ads_insights_performance_trend` (`hide_ui: true`),
   `ads_insights_industry_benchmark`, and `ads_get_errors` for anything
   blocking delivery.
5. Map each campaign to its app via `apps.md`.

Notes on the metrics:
- Use `results` / `cost_per_result` as installs / cost per install.
  `mobile_app_install` only counts SDK app events, and the apps don't have the
  Meta SDK.
- iOS install results come through SKAdNetwork and arrive 1–3 days late, so
  the last couple of days undercount iOS. Say so when it matters.

### Step 2 — Assess

For each campaign, judge it against the goal (maximize installs):
- **Learning phase:** a new or recently edited ad set needs ~7 days (and ideally
  ~50 results/week, which $5/day usually won't reach) before results are
  reliable. Don't recommend big changes from a few days of data, and remember
  that most edits restart learning.
- **Efficiency signals:** cost per result vs. the previous window and the
  benchmark; CPM (auction pressure / audience); CTR (creative pull); frequency
  (fatigue when it's above ~3 in a week for a small audience); spend pacing
  vs. budget.
- **Effectiveness signals:** total results and the trend; which ads win within
  an ad set; placements or creatives that aren't delivering; anything stuck in
  review, disapproved, or `WITH_ISSUES`.
- **Low-quality clicks:** a CTR above ~5% at a CPM below ~$1 usually means
  accidental taps (Audience Network, cheap markets), not real interest. Treat it
  as a red flag, not a success.
- Separate **observations** (anomalies, trends) from **causes**. Only state a
  cause when the data supports it.

### Step 3 — Recommend

- Rank by expected impact. Label each one **Efficiency** or **Effectiveness**,
  and give: what to change (exact entity and setting), why (the data behind
  it), the expected effect, confidence (high / medium / low), and whether it
  restarts learning.
- Filter Meta's Opportunity Score recommendations through the user's
  preferences and `apps.md`. Don't suggest anything that conflicts with them
  (e.g. worldwide targeting for Activity Log, more than 2 ads per ad set at
  the current budget, copy with prices), or flag the conflict explicitly if
  the data really argues for it.
- Typical levers: pause the clearly losing ad in an ad set; refresh fatigued
  creative; move budget between platform campaigns of the same app; scale a
  campaign with a stable, below-benchmark cost per install (budget increases of
  about 20% at a time); fix delivery issues; widen targeting when CPM is high
  and delivery is limited.
- If nothing should change (e.g. still learning), say so. "Wait" is a valid
  recommendation.

### Step 4 — Report

1. **Headline:** total spend, results, and blended cost per result for the
   window, with change vs. the previous window. Plus the Opportunity Score
   (account-level only).
2. **Per app:** a table per app with one row per campaign — status, daily
   budget, spend, results, cost per result (with Δ%), CTR, CPM, frequency.
   Under it, 1–3 lines on what stands out, including the best and worst ad.
3. **Drafts / issues:** unpublished drafts, errors, disapprovals.
4. **Recommendations:** the ranked list from Step 3.
5. End by offering to apply specific recommendations, one confirmation per
   change.

## Presenting results

- One table per account: campaign name, ID, and spend with currency. Show
  `—` for campaigns with no spend in the window.
- Say which window the metrics cover.
- List drafts in a separate **Drafts** table: name, ID, daily budget, whether
  it has an ad set and ads, and any `active_errors` or `validation_status`
  other than `VALIDATED`. Call out anything that would block publishing (no
  ad set, no ads, ad set with no app/`promoted_object`).

## Changes

Anything that creates, updates, activates, pauses, or deletes an ad object
(`ads_create_*`, `ads_update_*`, `ads_activate_entity`, `*_delete`) can spend
money or change live ads. Describe the exact change and get an explicit "yes"
in chat before every such call — approval doesn't carry over to the next
change.

## Keeping this skill current

This skill is a living document. At the end of any Meta Ads session where
something new was learned, summarize proposed updates for the user's review
(don't edit until they approve), covering:
- new or completed rows and notes in `apps.md` (targeting, IDs, asset
  folders, campaigns);
- new preferences or corrections from the user;
- new Meta tool quirks, errors, or workarounds;
- changes to accounts, portfolios, Pages, or Instagram accounts in
  `reference.md`.
