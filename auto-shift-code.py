# -*- coding: utf-8 -*-
import requests, lxml.html, feedparser, time, smtplib, ssl, yaml, os, argparse, sys

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

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
    for codeResult in get_codes(config):
        try:
            apply_code(codeResult.code, config)
            successful_codes.append(codeResult)
        except:
            failed_codes.append(codeResult)
    
    if (
        (successful_codes or failed_codes)
        and config['notification_email_address']
        and config['notification_email_password']
        and config['notification_email_recipient']
    ):
        send_status_email(successful_codes, failed_codes, config)

def get_config():
    args = getArguments()
    try:
        config_file = yaml.load(open(os.path.join(__location__, 'config.yml'), 'r'))
    except:
        config_file = {}

    config = {
        'shift_username': args.u or (config_file['shift_username'] if 'shift_username' in config_file else ''),
        'shift_password': args.p or (config_file['shift_password'] if 'shift_password' in config_file else ''),
        'notification_email_recipient': args.r or (config_file['notification_email_recipient'] if 'notification_email_recipient' in config_file else ''),
        'notification_email_address': config_file['notification_email_address'] if 'notification_email_address' in config_file else '',
        'notification_email_password': config_file['notification_email_password'] if 'notification_email_password' in config_file else '',
        'lookback_time_multiplier': args.m or (config_file['lookback_time_multiplier'] if 'lookback_time_multiplier' in config_file else 1),
    }

    if (not config['shift_username'] or not config['shift_password']):
        raise Exception('Missing SHiFT username or password. Check your command line arguments or config.yml file and try again.')

    return config

def getArguments():
    arg_parser = argparse.ArgumentParser('Applies BL3 SHiFT codes posted within the last hour to the specified SHiFT account.')
    arg_parser.add_argument("-u", default=None, help="The username of the SHiFT account")
    arg_parser.add_argument("-p", default=None, help="The password of the SHiFT account")
    arg_parser.add_argument("-r", default=None, help="The email address to which to send notification emails")
    arg_parser.add_argument("-m", default=None, help="The default amount of time this script looks back for new RSS feed items is 1 hour. Use this multiplier to increase that time.")
    return arg_parser.parse_args()

def get_codes(config):
    feed = feedparser.parse(CODE_FEED_LOCATION)
    return [{'code': entry.shift_code, 'reward': entry.shift_reward} for entry in feed.entries if time.mktime(time.gmtime()) - time.mktime(entry.published_parsed) < (ONE_HOUR * config['lookback_time_multiplier'])]

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
    parsed_rewards_response = lxml.html.fromstring(rewards_response.content)
    authenticity_token = parsed_rewards_response.xpath("/html/head/meta[@name='csrf-token']/@content")[0]

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
    parsed_check_token_response = lxml.html.fragments_fromstring(check_code_response.content)[1]
    authenticity_token = parsed_check_token_response.xpath("/html/body/form/input[@name='authenticity_token']/@value")[0]
    redemption_code = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[code]']/@value")[0]
    redemption_check = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[check]']/@value")[0]
    redemption_service = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[service]']/@value")[0]
    redemption_title = parsed_check_token_response.xpath("/html/body/form/input[@name='archway_code_redemption[title]']/@value")[0]
    commit = parsed_check_token_response.xpath("/html/body/form/input[@name='commit']/@value")[0]

    # submit code
    session.post(
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
                '\n'.join([f'{code_result["code"]} ({code_result["reward"]})' for code_result in successful_codes]) if successful_codes else 'N/A',
                '\n'.join([f'{code_result["code"]} ({code_result["reward"]})' for code_result in failed_codes]) if failed_codes else 'N/A',
            )
        )

if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()