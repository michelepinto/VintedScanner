#!/usr/bin/env python3
import sys
import Config
import logging
import requests
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Timeout configuration for the requests
timeoutconnection = 30

# List to keep track of already analyzed items
list_analyzed_items = set()

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
    #"DNT": "1",
    #"Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Priority": "u=0, i",
    "Sec-GPC": "1",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    #"Pragma": "no-cache",
    #"Cache-Control": "no-cache",
}

# Load previously analyzed item IDs to avoid duplicates
def load_analyzed_item():
    try:
        with open("vinted_items.txt", "r", errors="ignore") as f:
            for line in f:
                item_id = line.strip()
                if item_id:
                    list_analyzed_items.add(item_id)

    except FileNotFoundError:
        logger.info("No previous vinted_items.txt found, starting fresh")
    except IOError as e:
        logger.error(e, exc_info=True)
        sys.exit()

# Save a new analyzed item to prevent repeated alerts
def save_analyzed_item(item_id):
    try:
        with open("vinted_items.txt", "a") as f:
            f.write(str(item_id) + "\n")
    except IOError as e:
        logger.error(e, exc_info=True)
        sys.exit()

# Send a Telegram message when a new item is found
def send_telegram_message(item_title, item_price, item_url, item_image, favourite_count, seller):
    from html import escape

    safe_title = escape(str(item_title))

    if len(safe_title) > 33:
        safe_title = safe_title[:30] + "…"

    safe_url = escape(str(item_url), quote=True)

    caption_lines = [
        f'🔗 <a href="{safe_url}">{safe_title}</a>',
        f"💰 {item_price}" + (f" · ❤️ {favourite_count}" if favourite_count > 0 else ""),
    ]

    if seller:
        import pycountry
    
        country_iso_code = seller.get("country_iso_code", "N/A")
        country = pycountry.countries.get(alpha_2=country_iso_code)
    
        location = country.name if country else country_iso_code
    
        city = (seller.get("city") or "").strip()
    
        if city:
            location += f" · {city}"
    
        seller_info = (
            f"👤 {seller.get('login', 'N/D')} · "
            f"⭐ {seller.get('positive_feedback_count', 0)}/{seller.get('feedback_count', 0)}\n"
            f"📦 {seller.get('item_count', 0)} for sale · "
            f"{seller.get('total_items_count', 0)} total · "
            f"👥 {seller.get('followers_count', 0)}\n"
            f"📍 {location}"
        )
    
        caption_lines.append("")
        caption_lines.append(seller_info)

    caption = "\n".join(caption_lines)

    try:
        if item_image:
            url = f"https://api.telegram.org/bot{Config.telegram_bot_token}/sendPhoto"
            params = {
                "chat_id": Config.telegram_chat_id,
                "photo": item_image,
                "caption": caption,
                "parse_mode": "HTML",
            }
        else:
            url = f"https://api.telegram.org/bot{Config.telegram_bot_token}/sendMessage"
            params = {
                "chat_id": Config.telegram_chat_id,
                "text": caption,
                "parse_mode": "HTML",
            }

        response = requests.post(
            url,
            params=params,
            timeout=timeoutconnection
        )

        if response.status_code != 200:
            logger.error(
                f"Telegram notification failed. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
        else:
            logger.info("Telegram notification sent: %s", item_url)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {e}")

def normalize(text):
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(text))
        if not unicodedata.combining(c)
    ).lower()

def load_excluded_keywords():
    keywords = set()

    try:
        with open("excluded_keywords.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                keyword = line.strip()

                if keyword and not keyword.startswith("#"):
                    keywords.add(normalize(keyword))

        logger.info("Loaded %s excluded keywords", len(keywords))

    except FileNotFoundError:
        logger.info("No excluded_keywords.txt found, no keywords will be excluded")

    except IOError as e:
        logger.error(e, exc_info=True)
        sys.exit()

    return keywords


def is_excluded2(item_title, item_description, excluded_keywords):
    if not excluded_keywords:
        return False

    text = normalize(f"{item_title} {item_description}")

    return any(keyword in text for keyword in excluded_keywords)


def is_excluded(item_title, item_description, excluded_keywords):
    if not excluded_keywords:
        return False

    text = normalize(f"{item_title} {item_description}")

    if "chimica" in text:
        logger.info(
            "DEBUG CHIMICA | title=%r | description=%r | keyword_found=%s",
            item_title,
            item_description,
            any(keyword in text for keyword in excluded_keywords)
        )

    return any(keyword in text for keyword in excluded_keywords)

def get_user_details(user_id, session):
    try:
        url = f"{Config.vinted_url}/api/v2/users/{user_id}"

        response = session.get(
            url,
            headers=headers,
            timeout=timeoutconnection,
        )

        logger.info(
            "Vinted seller request: %s | status: %s",
            response.url,
            response.status_code
        )

        response.raise_for_status()

        data = response.json()

        return data.get("user")

    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Unable to fetch Vinted user {user_id}: {e}")
        return None

def main():
    
    vinted_url = Config.vinted_url

    # Load the list of previously analyzed items
    logger.info("Loading the list of previously analyzed items")
    load_analyzed_item()

    # Load excluded keywords
    excluded_keywords = load_excluded_keywords()

    # Initialize session
    session = requests.Session()
    session.post(vinted_url, headers=headers, timeout=timeoutconnection)

    # Loop through each search query defined in Config.py
    for params in Config.queries:
        
        page = 1

        while page <= 2:
            params["page"] = page
        
            # Request items from the Vinted API based on the search parameters
            try:
                url = f"{Config.vinted_api_url}/svc-catalogue/items"

                response = session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeoutconnection,
                )
    
                logger.info("Vinted URL triggered: %s", response.url)
                
                response.raise_for_status()
                data = response.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                logger.error(f"Unable to fetch Vinted page {page}: {e}")
                break
    
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                logger.error(
                    "Vinted response did not contain an items list "
                    f"(status={response.status_code}, keys={list(data) if isinstance(data, dict) else 'N/A'})"
                )
                break
    
            logger.info("Vinted API has returned: %s items", len(items))
    
            # Process each item returned in the response

            ignored_items = 0
            already_notified_items = 0
            notified_items = 0
                    
            for item in items:
                item_id = str(item["id"])
                item_title = item["title"]

                item_box = item.get("item_box") or {}                
                item_description = item_box.get("accessibility_label") or ""
                
                item_url = vinted_url + item["url"]
    
                item_price_data = item.get("price") or {}
                amount = item_price_data.get("amount")
                item_amount = (
                    f"{float(amount):.2f}".replace(".", ",")
                    if amount is not None
                    else "N/D"
                )
                item_total_price_data = item.get("total_item_price") or {}
                total_amount = item_total_price_data.get("amount")
                item_total_amount = (
                    f"{float(total_amount):.2f}".replace(".", ",")
                    if total_amount is not None
                    else "N/D"
                )
                item_currency = '€'
                item_price = (
                    f"{item_amount} {item_currency} "
                    f"({item_total_amount} {item_currency} w/fee)"
                    if item_amount != "N/D" and item_total_amount != "N/D"
                    else "N/D"
                )
    
                favourite_count = item.get("favourite_count") or 0
    
                item_photo = item.get("photo") or {}
                item_image = item_photo.get("full_size_url")
    
                # Skip items whose title or description match any excluded keyword
                if is_excluded(item_title, item_description, excluded_keywords):
                    # logger.info(f"Skipping excluded item [{item_id}]: {item_title}")
                    ignored_items += 1
                    continue
    
                # Check if the item has already been analyzed to prevent duplicates
                if item_id not in list_analyzed_items:

                    notified_items += 1
                    
                    user = item.get("user") or {}
                    user_id = user.get("id")

                    seller = get_user_details(user_id, session)
                        
                    # Send Telegram notifications if configured
                    if Config.telegram_bot_token and Config.telegram_chat_id:
                        send_telegram_message(item_title, item_price, item_url, item_image, favourite_count, seller)
    
                    # Mark item as analyzed and save it
                    list_analyzed_items.add(item_id)
                    save_analyzed_item(item_id)

                else:
                    already_notified_items += 1

            logger.info(f"Items ignored: {ignored_items}")
            logger.info(f"Items already notified: {already_notified_items}")
            logger.info(f"Items notified: {notified_items}")

            # If fewer than 96 items were returned, this is the last page
            if len(items) < 96:
                break
    
            page += 1

if __name__ == "__main__":
    main()
