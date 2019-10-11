# SHiFT Code Auto Submitter

This script automatically retrieves BL3 SHiFT codes and applies them to your account.

### Prerequisites

* Python 3.X

### Setup
Install the required libraries,
```
pip install -r requirements.txt
```

### Configuration
Specify the details of your SHiFT account in the config.yml file
```
shift_username: person@example.com
shift_password: password123
```
If you wish to receive email notifications when SHiFT codes are applied, specify the credentials of a gmail account with "Access for less secure apps" setting enabled(See https://support.google.com/cloudidentity/answer/6260879?hl=en).
```
notification_email_address: example@gmail.com
notification_email_password: abcd1234
```
Finally, specify the address at which you would like to recieve notification emails.
```
notification_email_recipient: person@example.com
```

The script is configured to check for any codes published in the last hour. To ensure that any new codes that get published will get applied, set up a cronjob (or use Windows Task Scheduler) to run the script every hour.

cron definition:
```
0 * * * * python3 ~/auto-shift-code/auto-shift-code.py
```

## Acknowledgments

Thanks to the folks at the [SHiFT and VIP Code Archive](shift.orcicorn.com) gathering and publishing the codes to their awesome RSS feed.