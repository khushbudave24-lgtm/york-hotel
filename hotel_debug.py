import requests
import smtplib
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'

def main():
    print('Starting debug...')

    url = 'https://booking-com.p.rapidapi.com/v2/properties/list'
    headers = {
        'X-RapidAPI-Key': RAPIDAPI_KEY,
        'X-RapidAPI-Host': 'booking-com.p.rapidapi.com'
    }
    params = {
        'dest_id': '20114931',
        'search_type': 'city',
        'arrival_date': '2026-05-01',
        'departure_date': '2026-05-02',
        'adults': '2',
        'room_qty': '1',
        'price_filter_currencycode': 'USD',
        'languagecode': 'en-us',
        'order_by': 'popularity',
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print('Status: ' + str(response.status_code))
        data = response.json()

        print('TOP LEVEL KEYS: ' + str(list(data.keys()) if isinstance(data, dict) else type(data).__name__))

        if isinstance(data, dict):
            for key in list(data.keys())[:5]:
                val = data[key]
                if isinstance(val, list):
                    print('KEY ' + key + ' = list of ' + str(len(val)) + ' items')
                    if len(val) > 0 and isinstance(val[0], dict):
                        print('  FIRST ITEM KEYS: ' + str(list(val[0].keys())))
                        if 'hotel_id' in val[0]:
                            print('  hotel_id: ' + str(val[0]['hotel_id']))
                        if 'hotel_name' in val[0]:
                            print('  hotel_name: ' + str(val[0]['hotel_name']))
                        if 'min_total_price' in val[0]:
                            print('  min_total_price: ' + str(val[0]['min_total_price']))
                elif isinstance(val, dict):
                    print('KEY ' + key + ' = dict with keys: ' + str(list(val.keys())[:8]))
                    for subkey in list(val.keys())[:3]:
                        subval = val[subkey]
                        if isinstance(subval, list):
                            print('  ' + subkey + ' = list of ' + str(len(subval)) + ' items')
                            if len(subval) > 0 and isinstance(subval[0], dict):
                                print('    FIRST ITEM KEYS: ' + str(list(subval[0].keys())))
                                if 'hotel_id' in subval[0]:
                                    print('    hotel_id: ' + str(subval[0]['hotel_id']))
                                if 'hotel_name' in subval[0]:
                                    print('    hotel_name: ' + str(subval[0]['hotel_name']))
                                if 'min_total_price' in subval[0]:
                                    print('    min_total_price: ' + str(subval[0]['min_total_price']))
                        else:
                            print('  ' + subkey + ': ' + str(subval)[:80])
                else:
                    print('KEY ' + key + ': ' + str(val)[:80])

        raw = json.dumps(data)
        print('RAW FIRST 3000 CHARS:')
        print(raw[:3000])

        result_text = 'DEBUG RESULTS\n\n' + raw[:5000]
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'York PA Debug - API Response'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg.attach(MIMEText(result_text, 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print('Debug email sent!')

    except Exception as e:
        print('Error: ' + str(e))


if __name__ == '__main__':
    main()
