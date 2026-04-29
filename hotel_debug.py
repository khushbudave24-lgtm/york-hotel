import requests
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz
import os
import json

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'
TIMEZONE = 'America/New_York'

HOTELS = [
    {'name': 'Ramada York PA', 'booking_id': '342291', 'display': 'Ramada by Wyndham York'},
    {'name': 'Inn At York PA', 'booking_id': '290380', 'display': 'Inn at York'},
    {'name': 'Motel 6 York PA', 'booking_id': '375049', 'display': 'Motel 6 York PA'},
    {'name': 'Motel 6 North York PA', 'booking_id': '375049', 'display': 'Motel 6 North York PA'},
    {'name': 'Red Roof York PA', 'booking_id': '344413', 'display': 'Red Roof Inn York Downtown'},
    {'name': 'Days Inn York PA', 'booking_id': '311652', 'display': 'Days Inn and Suites York'},
    {'name': 'Quality Inn York East', 'booking_id': '291498', 'display': 'Quality Inn and Suites York East'},
]


def get_dates():
    et = pytz.timezone(TIMEZONE)
    today = datetime.now(et).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    return str(today), str(next_friday), str(next_saturday)


def debug_api():
    print('=== DEBUG MODE - Checking API response structure ===')
    dates = get_dates()
    checkin = dates[0]
    checkout = str(datetime.strptime(checkin, '%Y-%m-%d').date() + timedelta(days=1))

    print('Checkin: ' + checkin + ' Checkout: ' + checkout)
    print('Testing with Ramada York ID: 342291')

    url = 'https://booking-com.p.rapidapi.com/v2/hotels/room-list'
    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
    }
    params = {
        'hotel_id': '342291',
        'checkin_date': checkin,
        'checkout_date': checkout,
        'adults_number': '2',
        'room_number': '1',
        'currency': 'USD',
        'locale': 'en-us',
        'units': 'metric',
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print('Status code: ' + str(response.status_code))
        data = response.json()
        top_keys = list(data.keys()) if isinstance(data, dict) else 'list of ' + str(len(data)) + ' items'
        print('Top level keys: ' + str(top_keys))

        if isinstance(data, dict):
            for key in data.keys():
                val = data[key]
                if isinstance(val, list) and len(val) > 0:
                    print('Key ' + key + ' is a list with ' + str(len(val)) + ' items')
                    first = val[0]
                    if isinstance(first, dict):
                        print('  First item keys: ' + str(list(first.keys())))
                        for subkey in list(first.keys())[:5]:
                            print('    ' + subkey + ': ' + str(first[subkey])[:100])
                elif isinstance(val, dict):
                    print('Key ' + key + ' is a dict with keys: ' + str(list(val.keys())[:5]))
                else:
                    print('Key ' + key + ': ' + str(val)[:100])

        print('=== FULL RESPONSE FIRST 2000 CHARS ===')
        print(json.dumps(data)[:2000])

    except Exception as e:
        print('Debug error: ' + str(e))

    print('=== Also testing v1 endpoint ===')
    url_v1 = 'https://booking-com.p.rapidapi.com/v1/hotels/room-list'
    params_v1 = {
        'hotel_id': '342291',
        'checkin_date': checkin,
        'checkout_date': checkout,
        'adults_number': '2',
        'room_number': '1',
        'currency': 'USD',
        'locale': 'en-us',
        'units': 'metric',
    }
    try:
        response_v1 = requests.get(url_v1, headers=headers, params=params_v1, timeout=15)
        print('v1 Status code: ' + str(response_v1.status_code))
        data_v1 = response_v1.json()
        print('v1 top keys: ' + str(list(data_v1.keys()) if isinstance(data_v1, dict) else 'list'))
        print('v1 FIRST 2000 CHARS:')
        print(json.dumps(data_v1)[:2000])
    except Exception as e:
        print('v1 Debug error: ' + str(e))


if __name__ == '__main__':
    debug_api()
