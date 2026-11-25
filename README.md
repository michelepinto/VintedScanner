# Vinted Scanner

A lightweight Python application that monitors Vinted for newly listed items and sends automatic notifications through Telegram.

Vinted Scanner periodically checks your configured searches, identifies new listings, filters unwanted items using a customizable keyword blacklist, retrieves seller information and sends notifications with listing details.

It can run locally on any machine or server using cron, or automatically through GitHub Actions.

## Features

- **Automated monitoring:** Scan multiple Vinted searches in a single execution.
- **Telegram notifications:** Receive alerts with listing links, photos, prices and seller information.
- **Keyword exclusion:** Automatically filter unwanted listings using a customizable blacklist.
- **Smart keyword matching:** Case-insensitive and accent-insensitive matching, including Italian special characters.
- **Duplicate prevention:** Keep track of previously notified listings to avoid repeated alerts.
- **Seller information:** Retrieve seller username, feedback, number of active listings, total listings, followers and location.
- **Price information:** Display the listing price and the total price including Vinted buyer protection fees.
- **Configurable pagination:** Control how many pages are scanned for each search.
- **Diagnostic logging:** Track scanner activity and optionally identify which blacklist keyword excluded an item.
- **Flexible execution:** Run manually, through cron or using GitHub Actions.

## How it works

Each execution follows these steps:

1. Load previously notified listing IDs from `already_notified_items.txt`.
2. Load excluded keywords from `excluded_keywords.txt`.
3. Initialize an HTTP session with Vinted.
4. Execute each search configured in `Config.py`.
5. Retrieve listings from the Vinted catalogue endpoint, scanning up to the configured number of pages.
6. Check each listing against the exclusion keywords.
7. Skip listings that have already been notified.
8. Retrieve additional information about the seller.
9. Send a Telegram notification containing the listing information.
10. Save the listing ID to prevent duplicate notifications in future executions.

The scanner processes up to 96 listings per page and stops when fewer than 96 items are returned.

## Repository structure

| File | Description |
|---|---|
| `vinted_scanner.py` | Main scanner application |
| `Config.sample.py` | Example configuration |
| `Config.py` | Your private configuration (not included in Git) |
| `requirements.txt` | Python dependencies |
| `excluded_keywords.txt` | Optional keyword blacklist |
| `already_notified_items.txt` | Automatically generated notification history |
| `.github/workflows/` | GitHub Actions workflows |

## Requirements

- Python 3.9 or newer.
- A Vinted account is not required by the current implementation.
- A Telegram bot and chat ID for notifications.
- Internet connectivity.

Python dependencies:

- `requests`: HTTP requests to Vinted and Telegram.
- `pycountry`: Country information for seller details.

## Installation

Clone the repository:

```bash
git clone https://github.com/michelepinto/VintedScanner.git
cd VintedScanner
```

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Create your configuration file:

```bash
cp Config.sample.py Config.py
```

Edit `Config.py` with your Vinted marketplace, Telegram credentials and search queries.

**Important:** Never commit `Config.py` because it contains your Telegram bot token.

Add the following to `.gitignore`:

```gitignore
Config.py
__pycache__/
```

## Configuration

All application settings are managed through `Config.py`.

### Telegram settings

Create a Telegram bot using [@BotFather](https://t.me/BotFather).

Configure the credentials:

```python
telegram_bot_token = "YOUR_BOT_TOKEN"
telegram_chat_id = "YOUR_CHAT_ID"
```

To retrieve your chat ID:

1. Start a conversation with your bot.
2. Send it a message.
3. Open the following URL, replacing the token:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

4. Find `message.chat.id` in the response.

For groups, add the bot to the group and retrieve the group ID. For channels, add the bot as an administrator.

### Vinted marketplace

Configure the marketplace URLs according to your country:

```python
vinted_url = "https://www.vinted.it"
vinted_api_url = "https://api.vinted.it"
```

Examples for other marketplaces:

| Country | Marketplace URL | API URL |
|---|---|---|
| Italy | `https://www.vinted.it` | `https://api.vinted.it` |
| France | `https://www.vinted.fr` | `https://api.vinted.fr` |
| Germany | `https://www.vinted.de` | `https://api.vinted.de` |
| Spain | `https://www.vinted.es` | `https://api.vinted.es` |

The storefront and API URLs must always refer to the same marketplace.

### Pagination

Configure the number of pages to scan for each search:

```python
pages = 3
```

Each page can contain up to 96 listings.

For example:

- `pages = 1`: Up to 96 listings per search.
- `pages = 3`: Up to 288 listings per search.
- `pages = 5`: Up to 480 listings per search.

The scanner stops earlier if Vinted returns fewer than 96 listings.

### Search queries

You can configure multiple independent searches in the `queries` list.

Example:

```python
queries = [
    {
        'search_text': '',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]': '417',
        'order': 'newest_first',
    },
    {
        'search_text': 't-shirt',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]': '',
        'order': 'newest_first',
    },
    {
        'search_text': '',
        'attribute_ids[catalog]': '2996',
        'attribute_ids[brand]': '',
        'order': 'newest_first',
    },
]
```

Available parameters:

| Parameter | Description |
|---|---|
| `search_text` | Free-text search. Can be left empty. |
| `attribute_ids[catalog]` | Vinted category ID. |
| `attribute_ids[brand]` | Vinted brand ID. |
| `order` | Search ordering. |

Supported ordering values include:

- `newest_first`
- `relevance`
- `price_high_to_low`
- `price_low_to_high`

For monitoring newly published listings, `newest_first` is recommended.

You can combine keywords, categories and brands to create more specific searches.

**Finding category and brand IDs**

The easiest way is to navigate to Vinted, apply your desired filters and inspect the resulting URL.

The numeric IDs are included in the search URL as query parameters.

For example:

- Brand ID `417`: Louis Vuitton.
- Category ID `2996`: Example category from the Vinted catalogue.

The IDs may vary as Vinted changes its catalogue.

## Excluding unwanted listings

The scanner supports a customizable blacklist through `excluded_keywords.txt`.

Create the file in the project root directory:

```text
# Unwanted or irrelevant listings

replica
fake
counterfeit
bundle
cover
broken
damaged
chimica
```

Add one keyword per line.

Lines starting with `#` and empty lines are ignored.

### How keyword filtering works

The scanner checks both:

- Listing title.
- Listing accessibility description (`accessibility_label`).

Matching is:

- Case-insensitive.
- Accent-insensitive.
- Based on substring matching.

For example, the keyword:

```text
chimica
```

will match:

- `Chimica`
- `CHIMICA`
- `Prodotto di chimica`
- `chimicà`

The normalization process uses Unicode NFKD decomposition, removing accent differences before comparison.

**Important:** Matching uses substrings, not complete words. For example, `top` will also match `laptop`.

Excluded listings are not added to the notification history. They will therefore be checked again during subsequent executions.

If you remove a keyword from the blacklist, previously excluded listings can become eligible for notification.

### Debugging excluded listings

To display which keyword caused a listing to be excluded:

```bash
python3 vinted_scanner.py --log_excluded
```

Example log:

```text
INFO Excluded item [123456789] - matching keyword: 'chimica'
```

This is particularly useful when investigating why a listing is being filtered or why an expected notification was not sent.

## Telegram notifications

When a new listing is found, the scanner retrieves the seller's public profile and generates a Telegram notification.

If the listing has a photo, Telegram receives an image with a caption. Otherwise, a text message is sent.

Example:

```text
🔗 Louis Vuitton Pochette Accessoires

💰 85,00 € (89,70 € w/fee) · ❤️ 12

👤 seller_name · ⭐ 214/220
📦 37 for sale · 190 total · 👥 58
🇮🇹 Milano
```

Notification information includes:

- Listing title and direct link.
- Listing price.
- Total price including buyer protection fees.
- Number of favourites.
- Seller username.
- Positive feedback and total feedback.
- Number of active listings.
- Total number of listings.
- Number of followers.
- Seller country and city, when available.

The seller information is retrieved separately from Vinted. If the seller lookup fails, the listing can still be processed without seller details.

The current implementation formats prices using the euro symbol.

## Listing history and duplicate prevention

The scanner maintains a local file:

```text
already_notified_items.txt
```

This file contains the IDs of listings already processed.

Each ID is stored on a separate line.

Example:

```text
123456789
123456790
123456791
```

The file is automatically created and updated by the scanner.

Do not delete this file unless you intentionally want to reset the notification history.

Deleting it will cause existing listings to be treated as new and potentially generate duplicate notifications.

### Initial setup

To avoid receiving notifications for all existing listings when starting the scanner for the first time:

1. Leave `telegram_bot_token` and `telegram_chat_id` empty in `Config.py`.
2. Run the scanner once.
3. The scanner will process the configured searches and populate `already_notified_items.txt` without sending Telegram notifications.
4. Configure your Telegram credentials.
5. Run the scanner normally.

From that point onwards, notifications will be sent for newly discovered listings.

## Running the scanner

Execute manually:

```bash
python3 vinted_scanner.py
```

Disable Telegram notifications for a run:

```bash
python3 vinted_scanner.py --notification_disabled
```

Display excluded listings and their matching keywords:

```bash
python3 vinted_scanner.py --log_excluded
```

Both options can be combined:

```bash
python3 vinted_scanner.py --log_excluded --notification_disabled
```

The application writes timestamped logs to standard output, making it suitable for both interactive execution and scheduled environments.

## Scheduling with Cron

The scanner is designed to run periodically.

For example, to execute it every 15 minutes:

Open the crontab:

```bash
crontab -e
```

Add:

```cron
*/15 * * * * cd /path/to/VintedScanner && /usr/bin/python3 vinted_scanner.py >> /path/to/vinted_scanner.log 2>&1
```

Make sure to replace `/path/to/VintedScanner` with the actual project directory.

The working directory is important because the scanner reads and writes `already_notified_items.txt` and `excluded_keywords.txt` using relative paths.

## Running with GitHub Actions

GitHub Actions can be used to execute the scanner automatically without maintaining your own server.

The recommended approach is to:

1. Store your private configuration in GitHub Actions Secrets.
2. Create a scheduled workflow.
3. Install Python dependencies.
4. Generate `Config.py` from the stored secret.
5. Execute `vinted_scanner.py`.
6. Persist `already_notified_items.txt` between executions.

Example workflow structure:

```yaml
name: Vinted Scanner

on:
  workflow_dispatch:
  schedule:
    - cron: "*/15 * * * *"

permissions:
  contents: write

jobs:
  scan:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Create configuration
        env:
          VINTED_CONFIG: ${{ secrets.VINTED_CONFIG }}
        run: |
          printf '%s\n' "$VINTED_CONFIG" > Config.py

      - name: Run scanner
        run: python3 vinted_scanner.py

      - name: Commit notification history
        run: |
          touch already_notified_items.txt
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add already_notified_items.txt
          git diff --cached --quiet || git commit -m "Update Vinted notification history"
          git push
```

Create a repository secret named `VINTED_CONFIG` containing the complete contents of your private `Config.py`.

Ensure that GitHub Actions has permission to write to the repository.

**Note:** GitHub Actions scheduled workflows use UTC and are not guaranteed to start exactly at the configured time. They may be delayed during periods of high load.

If you use multiple independent workflows, ensure they do not overwrite each other's notification history. A shared state file should be protected against concurrent writes.

## Troubleshooting

| Problem | Possible solution |
|---|---|
| `ModuleNotFoundError: No module named 'Config'` | Copy `Config.sample.py` to `Config.py`. |
| `AttributeError: module 'Config' has no attribute 'pages'` | Check that `pages` is defined in `Config.py`. |
| No Telegram notifications | Verify your bot token and chat ID. |
| Telegram error 400 | Check the chat ID and message parameters. |
| Telegram error 403 | Start the bot or check its permissions in the group/channel. |
| No listings returned | Check your search filters and marketplace URLs. |
| Unexpected listings | Review your configured queries and blacklist. |
| Expected listing excluded | Run with `--log_excluded` to identify the matching keyword. |
| Duplicate notifications | Check whether `already_notified_items.txt` is preserved between executions. |
| Seller details missing | The seller profile lookup may have failed. |

## Limitations and considerations

- The scanner uses Vinted's unofficial, undocumented internal API endpoints. They can change without notice.
- Vinted may apply rate limits or other restrictions to automated requests.
- Seller information requires an additional HTTP request for each new listing.
- The scanner currently supports Telegram notifications only.
- The currency symbol is currently hardcoded to EUR.
- Excluded listings are evaluated again on every execution.
- The notification history is stored locally, so scheduled environments must persist it between executions.

Use reasonable scanning intervals and respect Vinted's applicable terms and conditions.

## Credits

This project is based on the original [VintedScanner](https://github.com/drego85/VintedScanner) by Andrea Draghetti, with additional functionality and adaptations.

## License

GNU General Public License v3.0 (GPL-3.0).
