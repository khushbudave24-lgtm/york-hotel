import smtplib
import os
import time
import re
import urllib.request
import urllib.parse
import gzip
import ssl
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

SENDER_EMAIL    = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'
TIMEZONE        = 'America/New_York'

# 6 hotels — Quality Inn removed
HOTELS = [
    {'name': 'Ramada by Wyndham York', 'expedia_id': '108742'},
    {'name': 'Inn at York',             'expedia_id': '133853'},
    {'name': 'Motel 6 York PA',         'expedia_id': '127494'},
    {'name': 'Motel 6 North York PA',   'expedia_id': '127495'},
    {'name': 'Red Roof Inn York',       'expedia_id': '112953'},
    {'name': 'Days Inn York',           'expedia_id': '101337'},
]

YORK_EVENTS_ALL = [
    {'start': '2026-05-08', 'end': '2026-05-31', 'name': 'York Revolution Baseball Season',     'venue': 'PeoplesBank Park',          'impact': 'MODERATE'},
    {'start': '2026-06-03', 'end': '2026-08-30', 'name': 'Sounds of Summer Concert Series',     'venue': 'Downtown York',             'impact': 'MODERATE'},
    {'start': '2026-06-05', 'end': '2026-06-07', 'name': 'York Expo Arts and Crafts Show',      'venue': 'York Expo Center',          'impact': 'MODERATE'},
    {'start': '2026-06-13', 'end': '2026-06-13', 'name': 'York County Pride Festival',          'venue': 'York',                      'impact': 'MODERATE'},
    {'start': '2026-06-19', 'end': '2026-06-20', 'name': 'Penn-Mar Irish Festival',             'venue': 'York County',               'impact': 'MODERATE'},
    {'start': '2026-06-22', 'end': '2026-06-26', 'name': 'Lincoln Highway Conference',          'venue': 'York',                      'impact': 'HIGH'},
    {'start': '2026-07-06', 'end': '2026-07-11', 'name': 'Mason-Dixon Fair',                    'venue': 'York Fairgrounds Delta PA', 'impact': 'HIGH'},
    {'start': '2026-07-24', 'end': '2026-07-26', 'name': 'Smoke on the Rail BBQ Festival',     'venue': 'York Expo Center',          'impact': 'HIGH'},
    {'start': '2026-07-24', 'end': '2026-08-02', 'name': 'York State Fair',                    'venue': 'York Expo Center',          'impact': 'HIGH'},
    {'start': '2026-08-15', 'end': '2026-10-25', 'name': 'Pennsylvania Renaissance Faire',     'venue': 'Mount Hope Estate',         'impact': 'MODERATE'},
    {'start': '2026-09-17', 'end': '2026-09-20', 'name': 'Wild and Uncommon Weekend',          'venue': 'Horn Farm Center',          'impact': 'MODERATE'},
    {'start': '2026-09-19', 'end': '2026-09-20', 'name': 'York County Oyster Festival',        'venue': 'York',                      'impact': 'MODERATE'},
    {'start': '2026-11-27', 'end': '2026-11-28', 'name': 'Thanksgiving Holiday Weekend',       'venue': 'York Area',                 'impact': 'HIGH'},
    {'start': '2026-12-01', 'end': '2026-12-31', 'name': 'Christmas Magic Festival of Lights', 'venue': 'York County',               'impact': 'MODERATE'},
    {'start': '2027-02-06', 'end': '2027-02-08', 'name': 'Home and Garden Show',               'venue': 'York Expo Center',          'impact': 'HIGH'},
    {'start': '2027-03-14', 'end': '2027-03-14', 'name': 'York Saint Patricks Day Parade',     'venue': 'Downtown York',             'impact': 'MODERATE'},
    {'start': '2027-04-20', 'end': '2027-04-25', 'name': 'York Train Show',                    'venue': 'York Expo Center',          'impact': 'HIGH'},
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
]


def get_events():
    et       = pytz.timezone(TIMEZONE)
    today_dt = datetime.now(et).date()
    upcoming = [
        ev for ev in YORK_EVENTS_ALL
        if datetime.strptime(ev['end'], '%Y-%m-%d').date() >= today_dt
        and datetime.strptime(ev['start'], '%Y-%m-%d').date() <= today_dt + timedelta(days=60)
    ]
    upcoming.sort(key=lambda x: x['start'])
    return upcoming[:8]


def get_today():
    et = pytz.timezone(TIMEZONE)
    return str(datetime.now(et).date())


def make_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def fetch_html(url, referer=None):
    headers = {
        'User-Agent':      random.choice(USER_AGENTS),
        'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Cache-Control':   'no-cache',
        'DNT':             '1',
        'Connection':      'keep-alive',
    }
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20, context=make_ctx()) as r:
        raw = r.read()
        try:
            return gzip.decompress(raw).decode('utf-8', errors='ignore')
        except Exception:
            return raw.decode('utf-8', errors='ignore')


def parse_price(text, min_p=40, max_p=500):
    patterns = [
        r'"totalPricePerNight"\s*:\s*\{"formatted"\s*:\s*"\$([\d,]+)"',
        r'"price"\s*:\s*\{"lead"\s*:\s*\{"amount"\s*:\s*([\d.]+)',
        r'"amount"\s*:\s*([\d.]+)\s*,\s*"currencyCode"\s*:\s*"USD"',
        r'"totalRate"\s*:\s*"?([\d.]+)"?',
        r'"lowestRate"\s*:\s*"?([\d.]+)"?',
        r'\$\s*(\d{2,3})(?:\.\d{2})?\s*/\s*night',
        r'\$\s*(\d{2,3})(?:\.\d{2})?\s*per\s*night',
        r'[Ff]rom\s*\$\s*(\d{2,3})(?!\d)',
        r'[Ss]tarting\s*(?:at\s*)?\$\s*(\d{2,3})(?!\d)',
    ]
    for pat in patterns:
        matches = re.findall(pat, text)
        valid   = [int(float(m.replace(',', ''))) for m in matches
                   if min_p <= int(float(m.replace(',', ''))) <= max_p]
        if valid:
            return '$' + str(min(valid))
    return None


def try_google(hotel_name, checkin):
    query = hotel_name + ' hotel price tonight ' + checkin + ' York PA'
    url   = 'https://www.google.com/search?q=' + urllib.parse.quote(query) + '&hl=en&gl=us&num=5'
    try:
        html = fetch_html(url)
        kw   = hotel_name.lower().split()[0]
        idx  = html.lower().find(kw)
        area = html[max(0, idx - 200):idx + 3000] if idx > 0 else html[:8000]
        for pat in [
            r'[Ff]rom\s*\$\s*(\d{2,3})(?!\d)',
            r'\$\s*(\d{2,3})(?!\d)\s*/\s*night',
            r'\$\s*(\d{2,3})(?!\d)\s*per\s*night',
        ]:
            matches = re.findall(pat, area)
            valid = [int(m) for m in matches if 50 <= int(m) <= 400]
            if valid:
                print('    google: $' + str(min(valid)))
                return '$' + str(min(valid))
    except Exception as e:
        print('    google err: ' + str(e)[:60])
    return None


def try_expedia(hotel_name, expedia_id, checkin):
    checkout = str(datetime.strptime(checkin, '%Y-%m-%d').date() + timedelta(days=1))
    url = 'https://www.expedia.com/h' + expedia_id + '.Hotel-Information?chkin=' + checkin + '&chkout=' + checkout + '&rm1=a2'
    try:
        time.sleep(random.uniform(4, 7))
        html  = fetch_html(url, referer='https://www.expedia.com/')
        kw    = hotel_name.lower().split()[0]
        idx   = html.lower().find(kw)
        chunk = html[max(0, idx):idx + 3000] if idx > 0 else html
        price = parse_price(chunk)
        if price:
            print('    expedia: ' + price)
            return price
    except Exception as e:
        print('    expedia err: ' + str(e)[:60])
    return None


def try_booking(hotel_name, checkin):
    checkout = str(datetime.strptime(checkin, '%Y-%m-%d').date() + timedelta(days=1))
    url = ('https://www.booking.com/searchresults.html?ss='
           + urllib.parse.quote(hotel_name + ' York Pennsylvania')
           + '&checkin=' + checkin + '&checkout=' + checkout
           + '&group_adults=2&no_rooms=1&lang=en-us')
    try:
        time.sleep(random.uniform(3, 5))
        html  = fetch_html(url, referer='https://www.booking.com/')
        kw    = hotel_name.lower().split()[0]
        idx   = html.lower().find(kw)
        chunk = html[max(0, idx):idx + 3000] if idx > 0 else html[:8000]
        price = parse_price(chunk)
        if price:
            print('    booking: ' + price)
            return price
    except Exception as e:
        print('    booking err: ' + str(e)[:60])
    return None


def fetch_rate(hotel, checkin):
    name = hotel['name']
    eid  = hotel['expedia_id']
    for label, fn in [
        ('google',  lambda: try_google(name, checkin)),
        ('expedia', lambda: try_expedia(name, eid, checkin)),
        ('booking', lambda: try_booking(name, checkin)),
    ]:
        try:
            price = fn()
            if price:
                return price
        except Exception as e:
            print('    ' + label + ' err: ' + str(e)[:50])
        time.sleep(random.uniform(4, 8))
    return 'N/A'


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


def fmt_event_date(ev):
    s = datetime.strptime(ev['start'], '%Y-%m-%d')
    e = datetime.strptime(ev['end'],   '%Y-%m-%d')
    if ev['start'] == ev['end']:
        return s.strftime('%b ') + str(s.day)
    if s.month == e.month:
        return s.strftime('%b ') + str(s.day) + '-' + str(e.day)
    return s.strftime('%b ') + str(s.day) + ' - ' + e.strftime('%b ') + str(e.day)


def get_lowest(rates):
    vals = [int(rates[h['name']].replace('$', '')) for h in HOTELS
            if rates.get(h['name'], 'N/A') != 'N/A']
    return '$' + str(min(vals)) if vals else 'N/A'


def get_highest(rates):
    vals = [int(rates[h['name']].replace('$', '')) for h in HOTELS
            if rates.get(h['name'], 'N/A') != 'N/A']
    return '$' + str(max(vals)) if vals else 'N/A'


def build_email(rates, today_str, events):
    et  = pytz.timezone(TIMEZONE)
    now = datetime.now(et)
    send_time       = now.strftime('%B ') + str(now.day) + ', ' + str(now.year) + ' at 7:00 AM ET'
    lowest_tonight  = get_lowest(rates)
    highest_tonight = get_highest(rates)
    hotel_rows = ''
    for i, hotel in enumerate(HOTELS):
        rate  = rates.get(hotel['name'], 'N/A')
        color = rate_color(rate)
        hotel_rows += '<tr>'
        hotel_rows += '<td style=padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;color:#555;width:24px;>' + str(i + 1) + '.</td>'
        hotel_rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;font-size:13px;font-weight:600;color:#1a1a1a;>' + hotel['name'] + '</td>'
        hotel_rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;text-align:right;font-size:18px;font-weight:700;color:' + color + ';>' + rate + '</td>'
        hotel_rows += '</tr>'
    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            c   = '#c0392b' if imp == 'HIGH' else '#e07800' if imp == 'MODERATE' else '#2a7a2a'
            event_rows += '<tr><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;>'
            event_rows += '<span style=font-size:13px;font-weight:600;color:#1b2e1b;>' + ev['name'] + '</span><br>'
            event_rows += '<span style=font-size:11px;color:#999;>' + fmt_event_date(ev) + ' &bull; ' + ev['venue'] + '</span>'
            event_rows += '</td><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;text-align:right;>'
            event_rows += '<span style=background:' + c + ';color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;>' + imp + '</span>'
            event_rows += '</td></tr>'
    else:
        event_rows = '<tr><td colspan=2 style=padding:14px 8px;color:#888;font-size:13px;>No major events in the next 60 days.</td></tr>'
    html  = '<!DOCTYPE html><html><head><meta charset=UTF-8></head><body style=margin:0;padding:20px;background:#edeae3;font-family:Arial,sans-serif;>'
    html += '<div style=max-width:640px;margin:0 auto;background:#ffffff;border-radius:3px;overflow:hidden;box-shadow:0 4px 30px rgba(0,0,0,0.12);>'
    html += '<div style=background:#1b2e1b;padding:32px 36px;>'
    html += '<div style=font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#7eab6e;margin-bottom:8px;font-weight:600;>York, Pennsylvania - Daily Rate Report</div>'
    html += '<div style=font-size:26px;font-weight:700;color:#ffffff;margin-bottom:4px;>Hotel Rate Alert</div>'
    html += '<div style=font-size:12px;color:#9ab890;margin-bottom:16px;>Your 7:00 AM briefing - ' + send_time + '</div>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>Todays Rates</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>6 Properties</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;>Live Rates</span></div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=background:#1b2e1b;><tr>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + lowest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Lowest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + highest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Highest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;><div style=font-size:22px;font-weight:700;color:#ffffff;>6 Hotels</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Tracked Tonight</div></td></tr></table>'
    html += '<div style=padding:24px 36px 0;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;>Todays Rates - ' + fmt_date(today_str) + '</div></div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=padding:0 36px;><tbody>' + hotel_rows + '</tbody></table>'
    html += '<div style=padding:24px 36px 0;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;>York PA Events - Next 60 Days</div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=margin-bottom:24px;><tbody>' + event_rows + '</tbody></table></div>'
    html += '<div style=padding:12px 36px;background:#f7f4ef;border-top:1px solid #ebe7e0;><span style=font-size:11px;color:#888;>Rate Legend: <span style=color:#2a7a2a;font-weight:700;>Under $75 - Soft</span> | <span style=color:#e07800;font-weight:700;>$75-$99 - Moderate</span> | <span style=color:#c0392b;font-weight:700;>$100 and above - High</span></span></div>'
    html += '<div style=background:#1b2e1b;padding:18px 36px;text-align:center;><p style=font-size:11px;color:#5e8a5e;margin:0;line-height:1.8;>York PA Hotel Rate Alert - Sent daily at 7:00 AM ET<br>Ramada | Inn at York | Motel 6 x2 | Red Roof | Days Inn<br>Delivered to: khushbudave24@gmail.com</p></div>'
    html += '</div></body></html>'
    return html


def send_email(html_content, today_str):
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
    today_str = get_today()
    print('Today: ' + today_str)
    rates = {}
    for hotel in HOTELS:
        print('Fetching: ' + hotel['name'])
        rates[hotel['name']] = fetch_rate(hotel, today_str)
        print('=> ' + rates[hotel['name']])
        time.sleep(random.uniform(5, 10))
    events = get_events()
    print('Events: ' + str(len(events)))
    html = build_email(rates, today_str, events)
    send_email(html, today_str)
    print('Done!')


if __name__ == '__main__':
    main()
