#!/usr/bin/env python3
import sys
import time
import json
import Config
import smtplib
import logging
import requests
import email.utils
import unicodedata

from datetime import datetime
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler


# Configure a rotating file handler to manage log files
handler = RotatingFileHandler("vinted_scanner.log", maxBytes=5000000, backupCount=5)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

logger.info("Scanner started")


# Timeout configuration for the requests
timeoutconnection = 30

# List to keep track of already analyzed items
list_analyzed_items = set()

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "Priority": "u=0, i",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# Load previously analyzed item hashes to avoid duplicates
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
def save_analyzed_item(hash):
    try:
        with open("vinted_items.txt", "a") as f:
            f.write(str(hash) + "\n")
    except IOError as e:
        logger.error(e, exc_info=True)
        sys.exit()

# Send notification e-mail when a new item is found
def send_email(item_brand, item_title, item_price, item_url, item_image):
    try:
        # Create the e-mail message
        msg = EmailMessage()
        msg["To"] = Config.smtp_toaddrs
        msg["From"] = email.utils.formataddr(("Vinted Scanner", Config.smtp_username))
        msg["Subject"] = "Vinted Scanner - New Item"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid()

        # Format message content
        body_lines = [item_brand, item_title, str(item_price), f"🔗 {item_url}"]
        if item_image:
            body_lines.append(f"📷 {item_image}")
        body = "\n".join(body_lines)

        msg.set_content(body)
        
        # Securely opening the SMTP connection
        with smtplib.SMTP(Config.smtp_server, 587) as smtpserver:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()

            # Authentication
            smtpserver.login(Config.smtp_username, Config.smtp_psw)
            
            # Sending the message
            smtpserver.send_message(msg)
            logger.info("E-mail sent")
    
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)


# Send a Slack message when a new item is found
def send_slack_message(item_brand, item_title, item_price, item_url, item_image):
    webhook_url = Config.slack_webhook_url 

    # Format message content
    message_lines = [f"*🏷️ {item_brand}*", f"*🆕 {item_title}*", f"💰 {item_price}", f"🔗 {item_url}"]
    if item_image:
        message_lines.append(f"📷 {item_image}")
    message = "\n".join(message_lines)
    slack_data = {"text": message}

    try:
        response = requests.post(
            webhook_url, 
            data=json.dumps(slack_data),
            headers={"Content-Type": "application/json"},
            timeout=timeoutconnection
        )

        if response.status_code != 200:
            logger.error(f"Slack notification failed: {response.status_code}, {response.text}")
        else:
            logger.info("Slack notification sent")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Slack message: {e}")

# Send a Telegram message when a new item is found
def send_telegram_message(item_brand, item_title, item_price, item_url, item_image):
    from html import escape

    safe_brand = escape(str(item_brand))
    safe_title = escape(str(item_title))
    safe_url = escape(str(item_url), quote=True)
    
    caption = "\n".join([
        f'🔗 <a href="{safe_url}"><b>{safe_brand}</b> – {safe_title}</a>',
        f"💰 {item_price}",
    ])

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

        response = requests.post(url, params=params, headers=headers, timeout=timeoutconnection)

        if response.status_code != 200:
            logger.error(
                f"Telegram notification failed. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
        else:
            logger.info("Telegram notification sent")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {e}")

def normalize(text):
    return unicodedata.normalize("NFKD", text).lower()

def is_excluded(item_title, item_description, item_brand, excluded_keywords_str):
    if not excluded_keywords_str:
        return False

    keywords = [
        normalize(kw.strip())
        for kw in excluded_keywords_str.split(",")
        if kw.strip()
    ]
    text = normalize(f"{item_title} {item_description} {item_brand}")

    return any(kw in text for kw in keywords)

def main():

    # Load the list of previously analyzed items
    logger.info("Loading the list of previously analyzed items")
    load_analyzed_item()

    # Iterate over each Vinted market
    for market in Config.vinted_markets:

        market_name = market["name"]
        vinted_url = market["url"]
        vinted_api_url = market["api_url"]

        logger.info(
            "========================================"
        )
        logger.info(
            "Starting Vinted market: %s (%s)",
            market_name,
            vinted_url
        )
        logger.info(
            "========================================"
        )

        # Initialize session and obtain session cookies from Vinted
        logger.info(
            "[%s] Initializing session and obtaining session cookies",
            market_name
        )

        session = requests.Session()

        try:
            session.post(
                vinted_url,
                headers=headers,
                timeout=timeoutconnection
            )

            cookies = session.cookies.get_dict()

        except requests.exceptions.RequestException as e:
            logger.error(
                "[%s] Unable to initialize Vinted session: %s",
                market_name,
                e
            )
            continue

        # Loop through each search query
        for params in Config.queries:

            try:
                url = f"{vinted_api_url}/svc-catalogue/items"

                prepared_request = requests.Request(
                    "GET",
                    url,
                    params=params
                ).prepare()

                logger.info(
                    "[%s] Vinted URL triggered: %s",
                    market_name,
                    prepared_request.url
                )

                response = requests.get(
                    url,
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    timeout=timeoutconnection,
                )

                response.raise_for_status()

                data = response.json()

            except (requests.exceptions.RequestException, ValueError) as e:
                logger.error(
                    "[%s] Unable to fetch Vinted items: %s",
                    market_name,
                    e
                )
                continue

            items = data.get("items") if isinstance(data, dict) else None

            if not isinstance(items, list):

                logger.error(
                    "[%s] Vinted response did not contain an items list "
                    "(status=%s, keys=%s)",
                    market_name,
                    response.status_code,
                    list(data) if isinstance(data, dict) else "N/A"
                )

                continue

            logger.info(
                "[%s] Received %d items",
                market_name,
                len(items)
            )

            # Process each item
            for item in items:

                item_id = str(item["id"])

                item_brand = item.get("brand_title") or "N/A"

                item_title = item["title"]

                item_description = item.get("description") or ""

                item_url = vinted_url + item["url"]

                # Price
                item_price_data = item.get("price") or {}

                amount = item_price_data.get("amount")

                item_amount = (
                    f"{float(amount):.2f}".replace(".", ",")
                    if amount is not None
                    else "N/D"
                )

                # Total price
                item_total_price_data = (
                    item.get("total_item_price") or {}
                )

                total_amount = item_total_price_data.get("amount")

                item_total_amount = (
                    f"{float(total_amount):.2f}".replace(".", ",")
                    if total_amount is not None
                    else "N/D"
                )

                item_currency = "€"

                item_price = (
                    f"{item_amount} {item_currency} "
                    f"({item_total_amount} {item_currency} "
                    f"Includes Buyer Protection)"
                    if item_amount != "N/D"
                    and item_total_amount != "N/D"
                    else "N/D"
                )

                # Image
                item_photo = item.get("photo") or {}

                item_image = item_photo.get("full_size_url")

                # Excluded keywords
                if is_excluded(
                    item_title,
                    item_description,
                    item_brand,
                    Config.excluded_keywords
                ):

                    logger.info(
                        "[%s] Skipping excluded item [%s]: %s",
                        market_name,
                        item_id,
                        item_title
                    )

                    continue

                # Check if already analyzed
                if item_id not in list_analyzed_items:

                    logger.info(
                        "[%s] NEW ITEM [%s]: %s",
                        market_name,
                        item_id,
                        item_title
                    )

                    # Email
                    if Config.smtp_username and Config.smtp_server:
                        send_email(
                            item_brand,
                            item_title,
                            item_price,
                            item_url,
                            item_image
                        )

                    # Slack
                    if Config.slack_webhook_url:
                        send_slack_message(
                            item_brand,
                            item_title,
                            item_price,
                            item_url,
                            item_image
                        )

                    # Telegram
                    if (
                        Config.telegram_bot_token
                        and Config.telegram_chat_id
                    ):
                        send_telegram_message(
                            item_brand,
                            item_title,
                            item_price,
                            item_url,
                            item_image
                        )

                    # Mark as analyzed
                    list_analyzed_items.add(item_id)

                    save_analyzed_item(item_id)

if __name__ == "__main__":
    main()
