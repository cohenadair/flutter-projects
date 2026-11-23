# Meta Ads

Quirks of the Meta Ads MCP tools (`ads_*`) and Ads Manager, and how each
was resolved. Read this on any Meta error or unexpected result. The
`meta-ads` skill owns preferences and procedure; this file owns the fixes.

## Tool & Ads Manager quirks

- **"This tool is new and is being gradually rolled out across ad
  accounts"** for ad account 14363318: seen for `ads_creative_upload_media`
  (both `LOCAL_FILE` and `URL`) and `ads_creative_delete` (2026-10). Don't
  retry. Media: follow the `meta-ads` skill's **Media** section. Deleting a
  creative: leave it, or the user deletes it in Ads Manager.
- **`ads_get_ad_preview` returns inconsistent placements:** one request may
  return every placement, another only the one asked for. Request each
  placement you need explicitly.
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
- **"Ad account has no access to this Instagram account" (1815199)** on
  `ads_create_creative`, even though `ads_get_ig_accounts` lists the account
  and the ad account is a connected asset. The app's Facebook Page was owned
  by the user's personal profile, not the portfolio (Ads Manager's Page picker
  shows it under "Personal", and its Instagram account isn't offered). Fix:
  move both the Page and the Instagram account into Cohen Adair Apps, with the
  ad account added as a connected asset on each (Tapd, 2026-10-30).
- **Portfolios can't be merged.** Move individual assets (Instagram accounts,
  Pages) between portfolios instead; ad accounts can't be moved.
- **"App is Ineligible for Apple's SKAdNetwork" (3955033) / "No Opt Out
  Data" (3955014):** Meta won't run iOS 14+ install ads for that app without
  the Meta SDK (seen for Activity Log, which never had it; Anglers' Log
  passes). Checking the app's store IDs, ad account authorization, business
  ownership, the iOS 14+ agreement, or creating a new Meta app didn't help.
  Don't keep creating test campaigns — each leaves a draft the user has to
  discard. Building the campaign in Ads Manager instead produces Aggregated
  Event Measurement ad sets that fail later edits the same way.
- **New draft campaigns can't be deleted with the tool** (`status: DELETED`
  fails with "New campaigns need to be either active or paused"). The user
  discards them in Ads Manager, so avoid throwaway test campaigns.
- **`ads_create_ad_set` can wrongly refuse** with "the parent campaign does not
  use CBO" for a campaign that was published from Ads Manager, even when it
  has a campaign budget. Setting the budget again via the tool stages a broken
  draft. Have the user create the ad sets in Ads Manager; `ads_create_ad` still
  works for adding the ads to them.
- **A deleted Meta app breaks campaigns that point to it.** A live ad set's
  app can't be changed, so rebuild the campaign on the new app ID and pause
  the old one.
- **"Objective APP_INSTALLS is invalid. Use one of: … OUTCOME_APP_PROMOTION"**
  blocks publishing a campaign created in Ads Manager that saved the legacy
  `APP_INSTALLS` objective. It shows on every ad set and ad, in both the tool
  and Ads Manager (whose "Review and publish" may just hang), and Ads Manager
  has no way to change it. Fix (2026-10-14, with the user's OK): on the
  **unpublished draft** campaign, `ads_update_entity` with `{"objective":
  "OUTCOME_APP_PROMOTION"}`, then publish everything with
  `ads_activate_entity`. Setup and SKAdNetwork attribution were kept.
- **`regional_regulated_categories` in drafts isn't a user setting.** Values
  like `IRELAND_FINSERV` / `AUSTRALIA_UNIVERSAL` appear just because those
  countries are targeted. They don't mean the "financial products and
  services" checkbox is ticked, so don't flag them (2026-10-14).
- **Per-placement video ads (`placement_videos`) get rewritten by Ads Manager**
  when the ad set's placements change. The rewritten creative can fail with
  unrelated errors (e.g. "WhatsApp number required" #2446880). The live ad is
  unaffected; have the user discard the ad's draft.
- **Audience Network delivering on manual placements.** Ads Manager's "spend
  on excluded placements" setting can have Audience Network on for ad sets
  built in Ads Manager, even though it isn't in the main placements list. In
  the API it shows only as `mobileexternal` in `targeting.page_types`, while
  `publisher_platforms` lists only Facebook/Instagram/Threads. It can't be
  cleared through the API: replacing `targeting` keeps the old `page_types`,
  and writing `page_types` fails with "Page types have been replaced with Ad
  placements" (1885366), which leaves a broken draft. Have the user untick it
  under "spend on excluded placements" in Ads Manager (fixed for Activity Log
  iOS, 2026-10-22; it had taken ~a third of that campaign's spend as
  accidental taps at a ~40% click-through rate).
