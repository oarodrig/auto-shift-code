import requests, lxml, feedparser, time, smtplib, ssl, yaml

ONE_HOUR = 3600
CODE_FEED_LOCATION = 'https://shift.orcicorn.com/tags/borderlands3/index.xml'
NOTIFICATION_TEMPLATE = """\
Subject: Shift Codes Status ({} Successful, {} Failed)

Successful
{}

Failed
{}
"""

def main():
    config = get_config()
    successful_codes = []
    failed_codes = []
    for code in get_codes():
        try:
            apply_code(code, config)
            successful_codes.append(code)
        except:
            failed_codes.append(code)
    
    if (successful_codes or failed_codes):
        send_status_email(successful_codes, failed_codes, config)

def get_config():
    with open('config.yml', 'r') as config:
        return yaml.load(config)

def get_codes():
    feed = feedparser.parse(CODE_FEED_LOCATION)
    return [entry.title for entry in feed.entries if time.time() - time.mktime(entry.published_parsed) < ONE_HOUR]

def apply_code(code, config):
    session = requests.session()

    # Get authenticity token and session cookie
    home_response = session.get('https://shift.gearboxsoftware.com/home')
    parsed_home_response = lxml.html.fromstring(home_response.content)
    authenticity_token = parsed_home_response.xpath("/html/head/meta[@name='csrf-token']/@content")[0]

    # log in
    login_response = session.post(
        'https://shift.gearboxsoftware.com/sessions',
        data={
            'utf8' : '✓',
            'authenticity_token': authenticity_token,
            'user[email]': config['shift_username'],
            'user[password]': config['shift_password'],
            'commit': 'SIGN IN'
        },
        headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://shift.gearboxsoftware.com',
            'referer': 'https://shift.gearboxsoftware.com/home?redirect_to=false',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
        },
        allow_redirects=False
    )

    # Get updated authenticity token from rewards page
    rewards_response = session.get(
        'https://shift.gearboxsoftware.com/rewards',
        headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://shift.gearboxsoftware.com/rewards',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
        }
    )
    authenticity_token = parsed_home_response.xpath("/html/head/meta[@name='csrf-token']/@content")[0]

    # check code
    check_code_response = session.get(
        'https://shift.gearboxsoftware.com/entitlement_offer_codes?code=' + code,
        headers={
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://shift.gearboxsoftware.com/rewards',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
            'x-csrf-token': authenticity_token,
            'x-requested-with': 'XMLHttpRequest'
        }
    )

    # parse code submission form values
    # TODO do this dynamically for all form fields returned, instead of hard-coding names
    parsed_check_token_response = lxml.html.fromstring(check_code_response.content)
    authenticity_token = parsed_check_token_response.xpath("/html/body/form/input[@name='authenticity_token']/@value")[0]
    redemption_code = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[code]']/@value")[0]
    redemption_check = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[check]']/@value")[0]
    redemption_service = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[service]']/@value")[0]
    redemption_title = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[title]']/@value")[0]
    commit = parsed_check_token_response.xpath("/html/body/form/input[@name='commit']/@value")[0]

    # submit code
    login_response = session.post(
        'https://shift.gearboxsoftware.com/code_redemptions',
        data={
            'utf8' : '✓',
            'authenticity_token': authenticity_token,
            'archway_code_redemption[code]': redemption_code,
            'archway_code_redemption[check]': redemption_check,
            'archway_code_redemption[service]': redemption_service,
            'archway_code_redemption[title]': redemption_title,
            'commit': commit
        },
        headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://shift.gearboxsoftware.com',
            'referer': 'https://shift.gearboxsoftware.com/rewards',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
        },
        allow_redirects=False
    )

def send_status_email(successful_codes, failed_codes, config):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as email_service:
        email_service.login(config['notification_email_address'], config['notification_email_password'])
        email_service.sendmail(
            config['notification_email_address'],
            config['notification_email_recipient'],
            NOTIFICATION_TEMPLATE.format(
                len(successful_codes),
                len(failed_codes),
                '\n'.join(successful_codes) if successful_codes else 'N/A',
                '\n'.join(failed_codes) if failed_codes else 'N/A',
            )
        )

if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()