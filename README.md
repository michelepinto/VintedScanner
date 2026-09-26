# Vinted Scanner

A small Python scanner that polls [Vinted](https://www.vinted.it) for newly listed items matching your saved searches and pushes them to **Telegram** as soon as they appear.

Vinted has no real-time alerting for new listings. This script fills that gap: it runs on a schedule (cron or GitHub Actions), keeps a local record of every item it has already seen, and only notifies you about genuinely new ones.

![Python](https://img.shields.io/badge/python-3.11-blue?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/notifications-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white)
![License](https://img.shields.io/badge/license-GPL--3.0-green?style=flat-square)

---

## Table of contents

- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Configuration](#configuration)
  - [Config.py reference](#configpy-reference)
  - [Building queries](#building-queries)
  - [Finding catalog and brand IDs](#finding-catalog-and-brand-ids)
- [Excluding keywords](#excluding-keywords)
- [Telegram setup](#telegram-setup)
- [What a notification looks like](#what-a-notification-looks-like)
- [State file](#state-file)
- [Running on a schedule](#running-on-a-schedule)
  - [Cron](#cron)
  - [GitHub Actions](#github-actions)
- [Known quirks and limitations](#known-quirks-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Credits and license](#credits-and-license)

---

## How it works

One run of `vinted_scanner.py` does the following:

1. Loads the IDs of items already seen from `already_notified_items.txt` into memory.
2. Loads exclusion keywords from `excluded_keywords.txt`, if that file exists.
3. Opens a `requests.Session` and hits the storefront once (`vinted_url`) with browser-like headers so the session picks up the cookies the catalogue API expects.
4. For every entry in `Config.queries`, requests `{vinted_api_url}/svc-catalogue/items` page by page, up to `Config.pages` pages. Treat any page with fewer than 96 items as the last page, and stop early.
5. For every item returned:
   - Skips it if the title or the item's accessibility label matches an excluded keyword.
   - Skips it if the item ID is already in the notified set.
   - Otherwise, fetches the seller's public profile (`{vinted_url}/api/v2/users/{id}`), sends a Telegram message, then records the ID in memory and appends it to `already_notified_items.txt`.
6. Logs a per-page tally of items ignored, already notified and newly notified.

Logging goes to **stdout** with timestamps, at `INFO` level. Nothing is written to a log file by the script itself.

## Repository layout

| Path | Purpose |
|---|---|
| `vinted_scanner.py` | The whole scanner. No CLI arguments — everything comes from `Config.py`. |
| `Config.sample.py` | Template configuration. Copy it to `Config.py` and edit. |
| `requirements.txt` | `requests`, `pycountry`. |
| `.github/workflows/_vinted-scanner-template.yml` | Reusable workflow: installs deps, materialises `Config.py` from a secret, runs the scanner, commits the state file back to `master`. |
| `.github/workflows/vinted-scanner-sample.yml` | Scheduled sample caller for one profile. |
| `Config.py` | **Not in the repo.** Your configuration — contains your bot token, so keep it out of git. |
| `excluded_keywords.txt` | **Optional, not in the repo.** One keyword per line. |
| `already_notified_items.txt` | Generated. One item ID per line; this is the deduplication state. |

## Requirements

- Python 3.9 or newer (CI pins 3.11)
- A Telegram bot token and a chat ID
- Dependencies from `requirements.txt`:
  - `requests` — all HTTP calls
  - `pycountry` — turns the seller's ISO country code into a readable country name

## Quick start

```bash
git clone https://github.com/michelepinto/VintedScanner.git
cd VintedScanner

pip3 install -r requirements.txt

cp Config.sample.py Config.py
# edit Config.py: bot token, chat ID, country URLs, queries

python3 vinted_scanner.py
```

Before the first real run, consider **priming the state file**: leave `telegram_bot_token` and `telegram_chat_id` empty and run the script once. It will walk every query and write every current item ID to `already_notified_items.txt` without notifying you, so you don't get flooded by a few hundred messages covering listings that were already there. Fill the Telegram values in afterwards and you'll only hear about genuinely new listings.

Add a `.gitignore` if you plan to push your own fork:

```gitignore
Config.py
__pycache__/
```

## Configuration

`Config.py` is imported as a normal Python module, so every name below must exist — a missing one raises `AttributeError` at runtime.

### Config.py reference

| Setting | Type | Notes |
|---|---|---|
| `telegram_bot_token` | `str` | From [@BotFather](https://t.me/BotFather). If this or the chat ID is empty, no message is sent — but items are still marked as seen. |
| `telegram_chat_id` | `str` | Your user, group or channel ID. |
| `vinted_url` | `str` | Storefront base URL, e.g. `https://www.vinted.it`. Used for the session bootstrap, item links and seller lookups. |
| `vinted_api_url` | `str` | API base URL, e.g. `https://api.vinted.it`. Must match the storefront's country. |
| `pages` | `int` | Pages to fetch per query. Falsy values fall back to 2. A page holds up to 96 items. |
| `queries` | `list[dict]` | One dict per saved search. See below. |

Change the TLD on both URLs together to scan another market — `.fr`, `.es`, `.de`, `.nl`, and so on.

### Building queries

Each entry in `queries` is passed straight through as query-string parameters. The `page` key is injected by the script, so you don't set it yourself.

```python
queries = [
    {
        'search_text': '',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]': '417',      # brand-only search
        'order': 'newest_first',
    },
    {
        'search_text': 't-shirt',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]': '',         # free-text search
        'order': 'newest_first',
    },
    {
        'search_text': '',
        'attribute_ids[catalog]': '2996',   # category-only search, e.g. e-book readers
        'attribute_ids[brand]': '',
        'order': 'newest_first',
    },
]
```

| Key | Meaning |
|---|---|
| `search_text` | Free-text keywords. Leave empty to match everything within the other filters. |
| `attribute_ids[catalog]` | Numeric category ID. Empty means all categories. |
| `attribute_ids[brand]` | Numeric brand ID. Empty means all brands. |
| `order` | `newest_first`, `relevance`, `price_high_to_low` or `price_low_to_high`. `newest_first` is what you want for alerting. |

Any other filter the catalogue endpoint accepts (price bounds, size, condition, …) can be added as an extra key — the dict is forwarded verbatim.

### Finding catalog and brand IDs

Apply the filters you want on the Vinted website, then read the numeric IDs out of the resulting URL's query string and copy them into your query dict. Brand `417`, for example, is Louis Vuitton; catalog `2996` is e-book readers.

## Excluding keywords

Create `excluded_keywords.txt` next to the script, one keyword per line. Lines starting with `#` and blank lines are ignored:

```text
# noise I never want to see
replica
fake
bundle
cover
```

Matching details worth knowing:

- Comparison is **case- and accent-insensitive**. Text is normalised with NFKD and stripped of combining marks, so `sacoche` matches `Sacoche` and `Sacôche`.
- A keyword is matched against the item **title plus the item's accessibility label** (a short description string Vinted returns alongside each listing).
- Matching is a plain **substring** test, not word-based. `top` will also exclude anything containing "laptop" — prefer longer, specific keywords.
- Excluded items are **not** written to `already_notified_items.txt`, so they are re-checked on every run. Removing a keyword makes matching items notifiable again.
- If the file is missing, nothing is excluded and the script just logs that fact.

## Telegram setup

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token into `telegram_bot_token`.
2. Get your chat ID:
   - **Direct messages:** send any message to your bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `message.chat.id`.
   - **Groups:** add the bot to the group, post a message, and use the same endpoint. Group IDs are negative.
   - **Channels:** add the bot as an administrator and use the `@channelname` or the numeric `-100…` ID.
3. Put the value in `telegram_chat_id`.

## What a notification looks like

Messages are sent as HTML. When the listing has a photo the script uses `sendPhoto` with the caption below; otherwise it falls back to `sendMessage`.

```text
🔗 Louis Vuitton Pochette Ac…
💰 85,00 € (89,70 € w/fee) · ❤️ 12

👤 someseller · ⭐ 214/220
📦 37 for sale · 190 total · 👥 58
📍 Italy · Milano
```

- The title is HTML-escaped and truncated to 30 characters plus an ellipsis when it runs past 33.
- The price line shows the asking price and, in brackets, the total including buyer protection. The currency symbol is hardcoded to `€`.
- The heart counter only appears when the listing has at least one favourite.
- The seller block is omitted if the profile lookup fails. The country name is resolved from the ISO code via `pycountry`, with the city appended when Vinted exposes one.

## State file

`already_notified_items.txt` is a flat list of item IDs, one per line, appended as items are notified. Delete it to reset the scanner — the next run will treat everything it finds as new, so re-prime it as described in [Quick start](#quick-start) if you don't want the flood.

## Running on a schedule

### Cron

```bash
crontab -e
```

```cron
*/15 * * * * cd /path/to/VintedScanner && /usr/bin/python3 vinted_scanner.py >> /path/to/vinted.log 2>&1
```

`cd` into the repository first: `already_notified_items.txt` and `excluded_keywords.txt` are opened as **relative paths**, so they land in the working directory rather than next to the script.

### GitHub Actions

The workflows run the scanner in CI and commit the updated state file back to `master`, which means the deduplication state survives between runs without any server of your own.

**`_vinted-scanner-template.yml`** is a reusable workflow (`workflow_call`) taking a single required secret, `vinted_config`. It:

1. Checks out the repo and sets up Python 3.11.
2. Installs `requirements.txt`.
3. Writes the contents of the `vinted_config` secret verbatim into `Config.py` via a heredoc.
4. Runs `python3 vinted_scanner.py`.
5. Merges the run's `already_notified_items.txt` with the copy on `origin/master` (`sort -u`), commits as `github-actions[bot]` and pushes. Same for `vinted_logs.txt`.

It declares `permissions: contents: write` so the default `GITHUB_TOKEN` can push, and a `concurrency` group of `vinted-scanner-master` with `cancel-in-progress: false`, so runs from different profiles queue up instead of racing each other to push.

**Caller workflows** are thin. Each one is a profile with its own schedule and its own config secret:

| Workflow | Schedule (UTC) | Secret |
|---|---|---|
| `vinted-scanner-sample.yml` | `7,22,37,52 * * * *` | `VINTED_CONFIG_SAMPLE` |

Both are every 15 minutes, offset by 5 minutes so the two jobs don't collide on the shared state file. Both also expose `workflow_dispatch` for manual runs from the Actions tab.

**Adding a profile:**

1. Create a repository secret, e.g. `VINTED_CONFIG_ALEX`, and paste the *entire contents* of that person's `Config.py` into it — no surrounding quotes, no extra indentation, since the value is inserted into the heredoc as-is.
2. Copy one of the caller workflows, rename it, pick cron minutes that don't clash with the existing ones, and point `secrets.vinted_config` at the new secret.

```yaml
name: Vinted Scanner Alex

on:
  workflow_dispatch:
  schedule:
    - cron: "2,17,32,47 * * * *"

permissions:
  contents: write

jobs:
  scan:
    uses: ./.github/workflows/_vinted-scanner-template.yml
    secrets:
      vinted_config: ${{ secrets.VINTED_CONFIG_ALEX }}
```

Notes on the CI setup:

- Cron in GitHub Actions is **UTC**, and scheduled runs are best-effort — they are frequently delayed during busy periods, so treat "every 15 minutes" as a target rather than a guarantee.
- `excluded_keywords.txt` is read from the checkout, so it has to be **committed to the repo** to take effect in CI. It is shared by every profile.
- Scheduled workflows are disabled automatically after 60 days without repository activity. The state-file commits count as activity, so this normally takes care of itself.
- Under Settings → Actions → General, workflow permissions must allow read *and* write for the push step to succeed.

## Known quirks and limitations

Things the code does today that are worth being aware of before you rely on it:

- **The "Commit updated logs" step fails.** The scanner logs to stdout and never creates `vinted_logs.txt`, so `cp vinted_logs.txt …` errors out and the job ends red even when the scan itself worked. Either drop that step, or produce the file:
  ```yaml
  - name: Run scanner
    run: python3 vinted_scanner.py 2>&1 | tee -a vinted_logs.txt
  ```
- **First CI run can fail on `already_notified_items.txt`** for the same reason: if no new items were found, the file was never created and `cp` fails. Committing an empty `already_notified_items.txt` to `master`, or adding `touch already_notified_items.txt vinted_logs.txt` before the copy, fixes it permanently.
- **The whole config lives in a secret**, bot token included. Anyone who can edit workflows in this repo can exfiltrate it — keep write access tight.
- **The state file is committed**, so on a public repo everyone can see the IDs of the listings you have been tracking.
- **No LICENSE file is present** even though the project is described as GPL-3.0. Add one if you publish a fork.
- **Unofficial API.** Vinted publishes no documented public API. Endpoint paths, parameter names and response shapes can change without notice, and aggressive polling can get you rate-limited or blocked. Keep the interval reasonable and check the platform's terms before running this at scale.
- **One extra request per new item.** Seller details are fetched individually, so a run that discovers many new items makes many calls in quick succession.
- **Currency is hardcoded to `€`.** Scanning a non-euro market will show the wrong symbol.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: No module named 'Config'` | `Config.py` doesn't exist. Copy it from `Config.sample.py`. |
| `AttributeError: module 'Config' has no attribute 'pages'` | A key is missing from `Config.py`. All six settings must be defined. |
| `Vinted response did not contain an items list` | The session wasn't accepted, the endpoint or parameters changed, or you're being rate-limited. Check the logged status code and the URL. |
| Nothing is ever notified | Token or chat ID empty, everything filtered out by `excluded_keywords.txt`, or every ID is already in `already_notified_items.txt`. The per-page tallies in the log tell you which. |
| Telegram notification failed, status 400 | Usually a bad `chat_id`, or a photo URL Telegram can't fetch. |
| Telegram notification failed, status 403 | The bot was never started by the user, or was removed from the group/channel. |
| Duplicate alerts after a CI run | The state-file commit didn't land — check the push step of the previous run. |
| Wrong country's listings | `vinted_url` and `vinted_api_url` point at different markets. |

## Credits and license

This project is a fork of [drego85/VintedScanner](https://github.com/drego85/VintedScanner) by Andrea Draghetti, reworked around a Telegram-only notification path, keyword exclusions, seller enrichment and a GitHub Actions runner.

Released under the **GNU General Public License v3.0**.
