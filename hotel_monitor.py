import smtplib
import os
import time
import json
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

RAPIDAPI_KEY    = os.environ.get('RAPIDAPI_KEY', '')
SENDER_EMAIL    = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'
TIMEZONE        = 'America/New_York'
API_HOST        = 'apidojo-booking-v1.p.rapidapi.com'

# Hotel IDs confirmed working - city: York (Pennsylvania) verified in logs
HOTELS = [
    {'name': 'Ramada by Wyndham York',      'id': '342291'},
    {'name': 'Inn at York',                  'id': '290380'},
    {'name': 'Motel 6 York PA',              'id': '375049'},
    {'name': 'Motel 6 North York PA',        'id': '491289'},
    {'name': 'Red Roof Inn York',            'id': '344413'},
    {'name': 'Days Inn York',                'id': '311652'},
    {'name': 'Quality Inn York East',        'id': '291498'},
]

YORK_EVENTS = [
    {'month': 2,  'name': 'Home and Garden Show',           'date': 'Feb 6-8',        'venue': 'York Expo Center',  'impact': 'HIGH'},
    {'month': 3,  'name': 'York Saint Patricks Day Parade', 'date': 'Mar 14',          'venue': 'Downtown York',     'impact': 'MODERATE'},
    {'month': 4,  'name': 'York Train Show',                'date': 'Apr 20-25',       'venue': 'York Expo Center',  'impact': 'HIGH'},
    {'month': 5,  'name': 'Give Local York',                'date': 'Apr 30 - May 1',  'venue': 'York County',       'impact': 'HIGH'},
    {'month': 5,  'name': 'York Revolution Baseball',       'date': 'May 2026',        'venue': 'WellSpan Park',     'impact': 'MODERATE'},
    {'month': 6,  'name': 'York County Pride',              'date': 'Jun 13',          'venue': 'York',              'impact': 'MODERATE'},
    {'month': 6,  'name': 'Lincoln Highway Conference',     'date': 'Jun 22-26',       'venue': 'York',              'impact': 'HIGH'},
    {'month': 7,  'name': 'York State Fair',                'date': 'Jul 24 - Aug 2',  'venue': 'York Expo Center',  'impact': 'HIGH'},
    {'month': 7,  'name': 'Mason-Dixon Fair',               'date': 'Jul 6-11',        'venue': 'York Fairgrounds',  'impact': 'HIGH'},
    {'month': 8,  'name': 'York State Fair continues',      'date': 'Through Aug 2',   'venue': 'York Expo Center',  'impact': 'HIGH'},
    {'month': 9,  'name': 'Wild and Uncommon Weekend',      'date': 'Sep 17-20',       'venue': 'Horn Farm Center',  'impact': 'MODERATE'},
    {'month': 10, 'name': 'Pennsylvania Renaissance Faire', 'date': 'Through Oct 25',  'venue': 'Mount Hope Estate', 'impact': 'MODERATE'},
    {'month': 12, 'name': 'Christmas Magic Festival',       'date': 'Dec seasonal',    'venue': 'York County',       'impact': 'MODERATE'},
]


def get_events():
    et = pytz.timezone(TIMEZONE)
    month = datetime.now(et).month
    return [e for e in YORK_EVENTS if e['month'] == month]


def get_dates():
    et = pytz.timezone(TIMEZONE)
    today = datetime.now(et).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday   = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    return str(today), str(next_friday), str(next_saturday)


def api_get(path, params):
    url = 'https://' + API_HOST + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'X-RapidAPI-Key':  RAPIDAPI_KEY,
        'X-RapidAPI-Host': API_HOST,
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def deep_find_prices(obj, depth=0):
    prices = []
    if depth > 8:
        return prices
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if any(p in kl for p in ['price', 'rate', 'amount', 'cost', 'total']):
                if isinstance(v, (int, float)) and 30 < v < 600:
                    prices.append(float(v))
                elif isinstance(v, str):
                    try:
                        f = float(v.replace('$','').replace(',',''))
                        if 30 < f < 600:
                            prices.append(f)
                    except Exception:
                        pass
                elif isinstance(v, dict):
                    for vk, vv in v.items():
                        if isinstance(vv, (int, float)) and 30 < vv < 600:
                            prices.append(float(vv))
            prices.extend(deep_find_prices(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            prices.extend(deep_find_prices(item, depth + 1))
    return prices


def fetch_rate(hotel_id, hotel_name, checkin):
    checkout = str(datetime.strptime(checkin, '%Y-%m-%d').date() + timedelta(days=1))

    # Method 1: v2/get-rooms
    try:
        data = api_get('/properties/v2/get-rooms', {
            'hotel_id':      hotel_id,
            'arrival_date':  checkin,
            'departure_date': checkout,
            'adults':        '2',
            'room_qty':      '1',
            'units':         'metric',
            'languagecode':  'en-us',
            'currency_code': 'USD',
        })
        prices = deep_find_prices(data)
        if prices:
            best = min(p for p in prices if p > 30)
            print('    rooms: $' + str(int(round(best))))
            return '$' + str(int(round(best)))
    except Exception as e:
        print('    rooms error: ' + str(e)[:60])

    time.sleep(1)

    # Method 2: detail endpoint
    try:
        data = api_get('/properties/detail', {
            'hotel_id':        hotel_id,
            'arrival_date':    checkin,
            'departure_date':  checkout,
            'adults':          '2',
            'room_qty':        '1',
            'currency_code':   'USD',
            'languagecode':    'en-us',
            'units':           'metric',
            'temperature_unit':'c',
        })
        item = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
        if item:
            prices = deep_find_prices(item)
            if prices:
                best = min(p for p in prices if p > 30)
                print('    detail: $' + str(int(round(best))))
                return '$' + str(int(round(best)))
    except Exception as e:
        print('    detail error: ' + str(e)[:60])

    return 'N/A'


def fetch_rates_for_date(checkin):
    rates = {}
    for hotel in HOTELS:
        print('  ' + hotel['name'])
        rate = fetch_rate(hotel['id'], hotel['name'], checkin)
        rates[hotel['name']] = rate
        print('  => ' + rate)
        time.sleep(1)
    return rates


def rate_color(rate_str):
    if rate_str == 'N/A':
        return '#888888'
    try:
        val = int(rate_str.replace('$', ''))
        if val >= 100:
            return '#c0392b'
        if val >= 75:
            return '#e07800'
        return '#2a7a2a'
    except Exception:
        return '#888888'


def fmt_date(d):
    dt = datetime.strptime(d, '%Y-%m-%d')
    return dt.strftime('%A, %B ') + str(dt.day) + ', ' + str(dt.year)


def get_lowest(rates):
    vals = [int(rates[h['name']].replace('$','')) for h in HOTELS if rates.get(h['name'],'N/A') != 'N/A']
    return '$' + str(min(vals)) if vals else 'N/A'


def get_highest(rates):
    vals = [int(rates[h['name']].replace('$','')) for h in HOTELS if rates.get(h['name'],'N/A') != 'N/A']
    return '$' + str(max(vals)) if vals else 'N/A'


def build_rows(rates, numbered):
    rows = ''
    for i, hotel in enumerate(HOTELS):
        rate  = rates.get(hotel['name'], 'N/A')
        color = rate_color(rate)
        rows += '<tr>'
        if numbered:
            rows += '<td style=padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;color:#555;width:24px;>' + str(i+1) + '.</td>'
        rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;font-size:13px;font-weight:600;color:#1a1a1a;>' + hotel['name'] + '</td>'
        rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;text-align:right;font-size:18px;font-weight:700;color:' + color + ';>' + rate + '</td>'
        rows += '</tr>'
    return rows


def build_email(all_rates, dates, events):
    today_str, friday_str, saturday_str = dates
    et  = pytz.timezone(TIMEZONE)
    now = datetime.now(et)
    send_time      = now.strftime('%B ') + str(now.day) + ', ' + str(now.year) + ' at 7:00 AM ET'
    today_rates    = all_rates.get(today_str, {})
    friday_rates   = all_rates.get(friday_str, {})
    saturday_rates = all_rates.get(saturday_str, {})
    today_rows     = build_rows(today_rates, True)
    friday_rows    = build_rows(friday_rates, False)
    saturday_rows  = build_rows(saturday_rates, False)
    lowest_tonight  = get_lowest(today_rates)
    highest_tonight = get_highest(today_rates)
    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            c   = '#c0392b' if imp == 'HIGH' else '#e07800' if imp == 'MODERATE' else '#2a7a2a'
            event_rows += '<tr><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;>'
            event_rows += '<span style=font-size:13px;font-weight:600;color:#1b2e1b;>' + ev['name'] + '</span><br>'
            event_rows += '<span style=font-size:11px;color:#999;>' + ev['date'] + ' - ' + ev['venue'] + '</span>'
            event_rows += '</td><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;text-align:right;>'
            event_rows += '<span style=background:' + c + ';color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;>' + imp + '</span>'
            event_rows += '</td></tr>'
    else:
        event_rows = '<tr><td colspan=2 style=padding:14px 8px;color:#888;font-size:13px;>No major events this month.</td></tr>'
    html  = '<!DOCTYPE html><html><head><meta charset=UTF-8></head><body style=margin:0;padding:20px;background:#edeae3;font-family:Arial,sans-serif;>'
    html += '<div style=max-width:640px;margin:0 auto;background:#ffffff;border-radius:3px;overflow:hidden;box-shadow:0 4px 30px rgba(0,0,0,0.12);>'
    html += '<div style=background:#1b2e1b;padding:32px 36px;>'
    html += '<div style=font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#7eab6e;margin-bottom:8px;font-weight:600;>York, Pennsylvania - Daily Rate Report</div>'
    html += '<div style=font-size:26px;font-weight:700;color:#ffffff;margin-bottom:4px;>Hotel Rate Alert</div>'
    html += '<div style=font-size:12px;color:#9ab890;margin-bottom:16px;>Your 7:00 AM briefing - ' + send_time + '</div>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>Today + Weekend</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>7 Properties</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;>Live via Booking.com API</span></div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=background:#1b2e1b;><tr>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + lowest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Lowest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + highest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Highest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;><div style=font-size:22px;font-weight:700;color:#ffffff;>7 Hotels</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Tracked Tonight</div></td></tr></table>'
    html += '<div style=padding:24px 36px 0;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;>Todays Rates - ' + fmt_date(today_str) + '</div></div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=padding:0 36px;><tbody>' + today_rows + '</tbody></table>'
    html += '<div style=padding:24px 36px 0;margin-top:10px;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:14px;>Following Weekend Rates</div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=margin-bottom:16px;border:1px solid #ebe7e0;border-radius:6px;overflow:hidden;>'
    html += '<thead><tr style=background:#f7f4ef;><th colspan=2 style=padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#555;>Friday - ' + fmt_date(friday_str) + '</th></tr></thead>'
    html += '<tbody>' + friday_rows + '</tbody></table>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=margin-bottom:24px;border:1px solid #ebe7e0;border-radius:6px;overflow:hidden;>'
    html += '<thead><tr style=background:#f7f4ef;><th colspan=2 style=padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#555;>Saturday - ' + fmt_date(saturday_str) + '</th></tr></thead>'
    html += '<tbody>' + saturday_rows + '</tbody></table></div>'
    html += '<div style=padding:0 36px;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;>York PA Events - Rate Impact Watch</div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=margin-bottom:24px;><tbody>' + event_rows + '</tbody></table></div>'
    html += '<div style=padding:12px 36px;background:#f7f4ef;border-top:1px solid #ebe7e0;><span style=font-size:11px;color:#888;>Rate Legend: <span style=color:#2a7a2a;font-weight:700;>Under $75 - Soft</span> | <span style=color:#e07800;font-weight:700;>$75-$99 - Moderate</span> | <span style=color:#c0392b;font-weight:700;>$100 and above - High</span></span></div>'
    html += '<div style=background:#1b2e1b;padding:18px 36px;text-align:center;><p style=font-size:11px;color:#5e8a5e;margin:0;line-height:1.8;>York PA Hotel Rate Alert - Sent daily at 7:00 AM ET<br>Ramada | Inn at York | Motel 6 x2 | Red Roof | Days Inn | Quality Inn East<br>Delivered to: khushbudave24@gmail.com</p></div>'
    html += '</div></body></html>'
    return html


def send_email(html_content, dates):
    today_str = dates[0]
    dt = datetime.strptime(today_str, '%Y-%m-%d')
    subject = 'York PA Hotel Rates - ' + dt.strftime('%B ') + str(dt.day) + ', ' + str(dt.year)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = SENDER_EMAIL
    msg['To']      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print('Email sent to ' + RECIPIENT_EMAIL)
    except Exception as e:
        print('Email failed: ' + str(e))
        raise


def main():
    print('York PA Hotel Rate Monitor starting...')
    dates = get_dates()
    today_str, friday_str, saturday_str = dates
    print('Dates: ' + today_str + ' ' + friday_str + ' ' + saturday_str)
    all_rates = {}
    for date in [today_str, friday_str, saturday_str]:
        print('--- ' + date + ' ---')
        all_rates[date] = fetch_rates_for_date(date)
        time.sleep(2)
    events = get_events()
    print('Events: ' + str(len(events)))
    html = build_email(all_rates, dates, events)
    send_email(html, dates)
    print('Done!')


if __name__ == '__main__':
    main()
