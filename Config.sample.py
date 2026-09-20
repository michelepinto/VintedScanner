# Telegram Token and ChatID for notification
telegram_bot_token = ""
telegram_chat_id = ""

# Vinted URLs: change the TLD according to your country (.fr, .es, etc.)
vinted_url = "https://www.vinted.it"
vinted_api_url = "https://api.vinted.it"

# Number of pages to scan for each request (default is 2)
pages = 3

# Vinted queries for research
# "search_text" is the free search field, this field may be empty if you wish to search for the entire brand.
# "attribute_ids[catalog]" is the category in which to eventually search, if the field is empty it will search in all categories. Vinted assigns a numeric ID to each category, e.g. 2996 is the ID for e-Book Reader
# "attribute_ids[brand]" if you want to search by brand. Vinted assigns a numeric ID to each brand, e.g. 417 is the ID for Louis Vuitton
# "order" you can change it to relevance, newest_first, price_high_to_low, price_low_to_high

queries = [
    {
        'search_text': '',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]' : '417',
        'order': 'newest_first',
    },
    {
        'search_text': 't-shirt',
        'attribute_ids[catalog]': '',
        'attribute_ids[brand]' : '',
        'order': 'newest_first',
    },
    {
        'search_text': '',
        'attribute_ids[catalog]': '2996',
        'attribute_ids[brand]' : '',
        'order': 'newest_first',
    },

]
