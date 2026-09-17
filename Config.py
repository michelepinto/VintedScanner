# SMTP Settings for e-mail notification
smtp_username = ""
smtp_psw = ""
smtp_server = ""
smtp_toaddrs = ["User <example@example.com>"]

# Slack WebHook for notification
slack_webhook_url = ""

# Telegram Token and ChatID for notification
telegram_bot_token = "8301438643:AAHNOUdXWKZUs3GsxX5Mfy8NhrzPUwk3vvE"
telegram_chat_id = "1589206206"

# Vinted URsL: change the TLD according to your country (.fr, .es, etc.)
vinted_url = "https://www.vinted.it"
vinted_api_url = "https://api.vinted.it"

# Comma-separated list of strings to exclude from results (case-insensitive)
excluded_keywords = ""

# Vinted queries for research
# "page", "per_page" and "order" you may not edit them
# "search_text" is the free search field, this field may be empty if you wish to search for the entire brand.
# "attribute_ids[catalog]" is the category in which to eventually search, if the field is empty it will search in all categories. Vinted assigns a numeric ID to each category, e.g. 2996 is the ID for e-Book Reader
# "attribute_ids[brand]" if you want to search by brand. Vinted assigns a numeric ID to each brand, e.g. 417 is the ID for Louis Vuitton
# "order" you can change it to relevance, newest_first, price_high_to_low, price_low_to_high

queries = [
    {
        'page': '1',
        'per_page': '100',
        'search_text': '',
        'attribute_ids[catalog]': '1904', #donna
        'attribute_ids[brand]' : '88', # ralph lauren
        'attribute_ids[size]': '1391, 1578', # L, 46
        'order': 'newest_first',
    },
    {
        'page': '1',
        'per_page': '100',
        'search_text': '',
        'attribute_ids[catalog]': '1195', # abbigliamento bambina
        'attribute_ids[brand]' : '88, 275446, 341007', # ralph lauren, il gufo, save the duck
        'attribute_ids[size]': '630, 631', # 11, 12 anni
        'order': 'newest_first',
    },
    {
        'page': '1',
        'per_page': '100',
        'search_text': 'anni 90',
        'attribute_ids[catalog]': '3327', # bambole
        'attribute_ids[brand]' : '9081', # barbie
        'order': 'newest_first',
    },
]
