#!/usr/bin/env python3
import sys
import time
import json
from urllib import response
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
    "Ssec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
    #"Pragma": "no-cache",
    #"Cache-Control": "no-cache",
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

# Save a new analyzed item to prevent repeated alerts
def save_log(log):
    try:
        with open("log.txt", "a") as f:
            f.write(str(log) + "\n")
    except IOError as e:
        logger.error(e, exc_info=True)
        sys.exit()


# Send notification e-mail when a new item is found
def send_email(item_title, item_price, item_url, item_image):
    try:
        # Create the e-mail message
        msg = EmailMessage()
        msg["To"] = Config.smtp_toaddrs
        msg["From"] = email.utils.formataddr(("Vinted Scanner", Config.smtp_username))
        msg["Subject"] = "Vinted Scanner - New Item"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid()

        # Format message content
        body_lines = [item_title, str(item_price), f"🔗 {item_url}"]
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
def send_slack_message(item_title, item_price, item_url, item_image):
    webhook_url = Config.slack_webhook_url 

    # Format message content
    message_lines = [f"*🆕 {item_title}*", f"💰 {item_price}", f"🔗 {item_url}"]
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
def send_telegram_message(item_title, item_price, item_url, item_image):
    from html import escape

    safe_title = escape(str(item_title))
    safe_url = escape(str(item_url), quote=True)
    
    caption = "\n".join([
        f'🔗 <a href="{safe_url}">{safe_title}</a>',
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
            logger.info("Telegram notification sent: %s", item_url)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {e}")

def normalize(text):
    return unicodedata.normalize("NFKD", text).lower()

def is_excluded(item_title, item_description, excluded_keywords_str):
    if not excluded_keywords_str:
        return False

    keywords = [
        normalize(kw.strip())
        for kw in excluded_keywords_str.split(",")
        if kw.strip()
    ]
    text = normalize(f"{item_title} {item_description}")

    return any(kw in text for kw in keywords)

def main():
    
    vinted_url = Config.vinted_url

    # Load the list of previously analyzed items
    logger.info("Loading the list of previously analyzed items")
    load_analyzed_item()

    # Initialize session and obtain session cookies from Vinted
    logger.info("Initializing session and obtain session cookies from Vinted")
    session = requests.Session()
    session.post(vinted_url, headers=headers, timeout=timeoutconnection)
    cookies = session.cookies.get_dict()

    # Loop through each search query defined in Config.py
    for params in Config.queries:
        # Request items from the Vinted API based on the search parameters
        try:
            url = f"{Config.vinted_api_url}/svc-catalogue/items"

            prepared_request = requests.Request(
                "GET",
                url,
                params=params
            ).prepare()

            logger.info("Vinted URL triggered: %s", prepared_request.url)

            response = requests.get(
                url,
                params=params,
                cookies=cookies,
                headers=headers,
                timeout=timeoutconnection,
            )

            print("Status code: %s", response.status_code)
            print("Response: %s", response.text[:5000])
            print("Response URL: %s", response.url)
            save_log(response.url)
            
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Unable to fetch Vinted items: {e}")

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            logger.error(
                "Vinted response did not contain an items list "
                f"(status={response.status_code}, keys={list(data) if isinstance(data, dict) else 'N/A'})"
            )
            continue

        logger.info("DATA_RESPONSE_KEYS: %s", data.keys())

        logger.info("RESPONSE HEADERS: %s", response.headers)

        logger.info("Vinted API has returned: %s items", len(items))

        # Process each item returned in the response
        for item in items:
            item_id = str(item["id"])
            item_title = item["title"]
            item_description = item.get("description") or ""
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
                f"({item_total_amount} {item_currency} With Fee)"
                if item_amount != "N/D" and item_total_amount != "N/D"
                else "N/D"
            )

            item_photo = item.get("photo") or {}
            item_image = item_photo.get("full_size_url")

            # Skip items whose title or description match any excluded keyword
            if is_excluded(item_title, item_description, Config.excluded_keywords):
                logger.info(f"Skipping excluded item [{item_id}]: {item_title}")
                continue

            # Check if the item has already been analyzed to prevent duplicates
            if item_id not in list_analyzed_items:

                # Send e-mail notifications if configured
                if Config.smtp_username and Config.smtp_server:
                    send_email(item_title, item_price, item_url, item_image)

                # Send Slack notifications if configured
                if Config.slack_webhook_url:
                    send_slack_message(item_title, item_price, item_url, item_image)

                # Send Telegram notifications if configured
                if Config.telegram_bot_token and Config.telegram_chat_id:
                    send_telegram_message(item_title, item_price, item_url, item_image)

                # Mark item as analyzed and save it
                list_analyzed_items.add(item_id)
                save_analyzed_item(item_id)

if __name__ == "__main__":
    main()
