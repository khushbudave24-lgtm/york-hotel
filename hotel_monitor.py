import smtplib
import os
import time
import re
import json
import urllib.request
import urllib.parse
import gzip
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

SENDER_EMAIL    = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'
TIMEZONE        = 'America/New_York'

HOTELS = [
    {
        'name':        'Ramada by Wyndham York',
        'brand_url':   'https://www.wyndhamhotels.com/ramada/york-pennsylvania/ramada-york/rooms-rates?checkInDate={checkin}&checkOutDate={checkout}&adults=2&rooms=1',
        'expedia_id':  '108742',
        'ta_id':       'd73394',
        'priceline_q': 'Ramada+by+Wyndham+York+Pennsylvania',
        'booking_q':   'Ramada by Wyndham York PA',
    },
    {
        'name':        'Inn at York',
        'brand_url':   'https://www.innatyork.com/rooms/?check_in={checkin}&check_out={checkout}&adults=2',
        'expedia_id':  '133853',
        'ta_id':       'd73399',
        'priceline_q': 'Inn+at+York+Pennsylvania',
        'booking_q':   'Inn at York PA',
    },
    {
        'name':        'Motel 6 York PA',
        'brand_url':   'https://www.motel6.com/en/home/motels.pa.york.4730.html?checkin={checkin}&checkout={checkout}&rooms=1&adults=2',
        'expedia_id':  '127494',
        'ta_id':       'd73401',
        'priceline_q': 'Motel+6+York+Pennsylvania',
        'booking_q':   'Motel 6 York PA',
    },
    {
        'name':        'Motel 6 North York PA',
        'brand_url':   'https://www.motel6.com/en/home/motels.pa.york.1028.html?checkin={checkin}&checkout={checkout}&rooms=1&adults=2',
        'expedia_id':  '127495',
        'ta_id':       'd73402',
        'priceline_q': 'Motel+6+North+York+Pennsylvania',
        'booking_q':   'Motel 6 North York PA',
    },
    {
        'name':        'Red Roof Inn York',
        'brand_url':   'https://www.redroof.com/property/pa/york/RRI687/?arrivalDate={checkin}&departureDate={checkout}&numAdults=2&numRooms=1',
        'expedia_id':  '112953',
        'ta_id':       'd73403',
        'priceline_q': 'Red+Roof+Inn+York+Pennsylvania',
        'booking_q':   'Red Roof Inn York PA',
    },
    {
        'name':        'Days Inn York',
        'brand_url':   'https://www.wyndhamhotels.com/days-inn/york-pennsylvania/days-inn-york/rooms-rates?checkInDate={checkin}&checkOutDate={checkout}&adults=2&rooms=1',
        'expedia_id':  '101337',
        'ta_id':       'd73404',
        'priceline_q': 'Days+Inn+York+Pennsylvania',
        'booking_q':   'Days Inn York PA',
    },
    {
        'name':        'Quality Inn York East',
        'brand_url':   'https://www.choicehotels.com/pennsylvania/york/quality-inn-hotels/pa423/rates?checkInDate={checkin}&checkOutDate={checkout}&adults=2&rooms=1',
        'expedia_id':  '112954',
        'ta_id':       'd73405',
        'priceline_q': 'Quality+Inn+Suites+York+East+Pennsylvania',
        'booking_q':   'Quality Inn York East PA',
    },
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


def get_dates():
    et    = pytz.timezone(TIMEZONE)
    today = datetime.now(et).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday   = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    return str(today), str(next_friday), str(next_saturday)


def make_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def fetch_html(url, ua=None):
    headers = {
        'User-Agent':      ua or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Cache-Control':   'no-cache',
        'Pragma':          'no-cache',
        'Connection':      'keep-alive',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=18, context=make_ctx()) as r:
        raw = r.read()
        try:
            return gzip.decompress(raw).decode('utf-8', errors='ignore')
        except Exception:
            return raw.decode('utf-8', errors='ignore')


def parse_price(html, min_p=40, max_p=500):
    patterns = [
        r'"totalPricePerNight"\s*:\s*\{"formatted"\s*:\s*"\$([\d,]+)"',
        r'"price"\s*:\s*\{"lead"\s*:\s*\{"amount"\s*:\s*([\d.]+)',
        r'"displayPrice"\s*:\s*\{"amount"\s*:\s*([\d.]+)',
        r'"totalPrice"\s*:\s*\{"amount"\s*:\s*([\d.]+)',
        r'"amount"\s*:\s*([\d.]+)\s*,\s*"currencyCode"\s*:\s*"USD"',
        r'"totalRate"\s*:\s*"?([\d.]+)"?',
        r'"lowestRate"\s*:\s*"?([\d.]+)"?',
        r'\$\s*(\d{2,3})(?:\.\d{2})?\s*/\s*night',
        r'\$\s*(\d{2,3})(?:\.\d{2})?\s*per\s*night',
        r'[Ff]rom\s*\$\s*(\d{2,3})(?!\d)',
        r'[Ss]tarting\s*(?:at\s*)?\$\s*(\d{2,3})(?!\d)',
    ]
    for pat in patterns:
        matches = re.findall(pat, html)
        valid   = [int(float(m.replace(',', ''))) for m in matches
                   if min_p <= int(float(m.replace(',', ''))) <= max_p]
        if valid:
            return '$' + str(min(valid))
    return None


# ── 1. Brand website ─────────────────────────────────────────────────────────
def try_brand(hotel, checkin, checkout):
    url = hotel['brand_url'].replace('{checkin}', checkin).replace('{checkout}', checkout)
    try:
        html  = fetch_html(url)
        price = parse_price(html)
        if price:
            print('    brand OK: ' + price)
            return price
    except Exception as e:
        print('    brand err: ' + str(e)[:60])
    return None


# ── 2. Expedia ────────────────────────────────────────────────────────────────
def try_expedia(hotel, checkin, checkout):
    eid  = hotel['expedia_id']
    name = hotel['name']
    urls = [
        'https://www.expedia.com/h' + eid + '.Hotel-Information?chkin=' + checkin + '&chkout=' + checkout + '&rm1=a2',
        'https://www.expedia.com/Hotel-Search?destination=' + urllib.parse.quote('York, Pennsylvania') + '&startDate=' + checkin + '&endDate=' + checkout + '&adults=2&rooms=1',
    ]
    for url in urls:
        try:
            html = fetch_html(url)
            # For search page, find hotel section first
            if 'Hotel-Search' in url:
                kw  = name.lower().split()[0]
                idx = html.lower().find(kw)
                if idx < 0:
                    continue
                html = html[idx:idx + 3000]
            price = parse_price(html)
            if price:
                print('    expedia OK: ' + price)
                return price
        except Exception as e:
            print('    expedia err: ' + str(e)[:60])
        time.sleep(1)
    return None


# ── 3. TripAdvisor ────────────────────────────────────────────────────────────
def try_tripadvisor(hotel, checkin, checkout):
    query = urllib.parse.quote(hotel['name'] + ' York Pennsylvania')
    url   = ('https://www.tripadvisor.com/Search?q=' + query
             + '&searchSessionId=x&sid=x&blockRedirect=true&ssrc=A&geo=52687'
             + '&checkin=' + checkin + '&checkout=' + checkout)
    try:
        html  = fetch_html(url, ua='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15')
        kw    = hotel['name'].lower().split()[0]
        idx   = html.lower().find(kw)
        chunk = html[max(0, idx):idx + 3000] if idx > 0 else html[:5000]
        price = parse_price(chunk)
        if price:
            print('    tripadvisor OK: ' + price)
            return price
    except Exception as e:
        print('    tripadvisor err: ' + str(e)[:60])
    return None


# ── 4. Priceline ──────────────────────────────────────────────────────────────
def try_priceline(hotel, checkin, checkout):
    q   = hotel['priceline_q']
    url = ('https://www.priceline.com/relax/at/' + q
           + '/from/' + checkin + '/to/' + checkout
           + '/rooms/1?adults=2')
    try:
        html  = fetch_html(url)
        price = parse_price(html[:40000])
        if price:
            print('    priceline OK: ' + price)
            return price
    except Exception as e:
        print('    priceline err: ' + str(e)[:60])
    return None


# ── 5. Booking.com ────────────────────────────────────────────────────────────
def try_booking(hotel, checkin, checkout):
    q   = urllib.parse.quote(hotel['booking_q'])
    url = ('https://www.booking.com/searchresults.html?ss=' + q
           + '&checkin=' + checkin + '&checkout=' + checkout
           + '&group_adults=2&no_rooms=1&group_children=0&lang=en-us')
    try:
        html  = fetch_html(url)
        kw    = hotel['name'].lower().split()[0]
        idx   = html.lower().find(kw)
        chunk = html[max(0, idx):idx + 3000] if idx > 0 else html[:8000]
        price = parse_price(chunk)
        if price:
            print('    booking OK: ' + price)
            return price
    except Exception as e:
        print('    booking err: ' + str(e)[:60])
    return None


def fetch_rate(hotel, checkin):
    checkout = str(datetime.strptime(checkin, '%Y-%m-%d').date() + timedelta(days=1))

    for source_fn in [try_brand, try_expedia, try_tripadvisor, try_priceline, try_booking]:
        price = source_fn(hotel, checkin, checkout)
        if price:
            return price
        time.sleep(2)

    return 'N/A'


def fetch_rates_for_date(checkin):
    rates = {}
    for hotel in HOTELS:
        print('  ' + hotel['name'])
        rates[hotel['name']] = fetch_rate(hotel, checkin)
        print('  => ' + rates[hotel['name']])
        time.sleep(2)
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


def build_rows(rates, numbered):
    rows = ''
    for i, hotel in enumerate(HOTELS):
        rate  = rates.get(hotel['name'], 'N/A')
        color = rate_color(rate)
        rows += '<tr>'
        if numbered:
            rows += '<td style=padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;color:#555;width:24px;>' + str(i + 1) + '.</td>'
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
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>Today + Weekend</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>7 Properties</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;>Live Rates</span></div>'
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
    html += '<div style=padding:0 36px;><div style=font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;>York PA Events - Next 60 Days</div>'
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
        time.sleep(3)
    events = get_events()
    print('Upcoming events: ' + str(len(events)))
    html = build_email(all_rates, dates, events)
    send_email(html, dates)
    print('Done!')


if __name__ == '__main__':
    main()
