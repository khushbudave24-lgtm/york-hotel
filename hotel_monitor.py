import anthropic
import smtplib
import os
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
SENDER_EMAIL      = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD   = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL   = 'khushbudave24@gmail.com'
TIMEZONE          = 'America/New_York'

HOTELS = [
    'Ramada by Wyndham York PA',
    'Inn at York PA',
    'Motel 6 York PA',
    'Motel 6 North York PA',
    'Red Roof Inn York PA',
    'Days Inn York PA',
    'Quality Inn and Suites York East PA',
]

YORK_EVENTS_ALL = [
    {'start': '2026-05-08', 'end': '2026-05-31', 'name': 'York Revolution Baseball Season',     'venue': 'PeoplesBank Park',          'impact': 'HIGH'},
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


def get_today():
    et = pytz.timezone(TIMEZONE)
    return str(datetime.now(et).date())


def fetch_rate_for_hotel(hotel_name, date_str, client):
    dt_obj      = datetime.strptime(date_str, '%Y-%m-%d')
    date_pretty = dt_obj.strftime('%B %d, %Y')
    prompt = (
        'Use your web search tool to search for: "'
        + hotel_name + ' York PA hotel room rate ' + date_pretty + '"\n\n'
        'Find the room rate from Google search results or any travel site.\n\n'
        'Return ONLY this JSON:\n'
        '{"rate": "$XX", "source": "site name"}\n\n'
        'Use the lowest price found. If not found: {"rate": "N/A", "source": "not found"}'
    )
    try:
        response = client.messages.create(
            model      = 'claude-haiku-4-5',
            max_tokens = 256,
            tools      = [{'type': 'web_search_20250305', 'name': 'web_search'}],
            messages   = [{'role': 'user', 'content': prompt}],
        )
        full_text = ''
        for block in response.content:
            if hasattr(block, 'text'):
                full_text += block.text
        start = full_text.find('{')
        end   = full_text.rfind('}') + 1
        if start >= 0 and end > start:
            data   = json.loads(full_text[start:end])
            rate   = data.get('rate', 'N/A')
            source = data.get('source', 'unknown')
            print('  ' + hotel_name + ': ' + rate + ' (' + source + ')')
            return rate, source
        print('  ' + hotel_name + ': no JSON')
        return 'N/A', 'not found'
    except anthropic.RateLimitError:
        print('  rate limit, waiting 60s')
        time.sleep(60)
        return 'N/A', 'rate limit'
    except Exception as e:
        print('  error: ' + str(e)[:80])
        return 'N/A', 'error'


def fetch_all_rates(date_str):
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    rates   = {}
    sources = {}
    for i, hotel in enumerate(HOTELS):
        rate, source   = fetch_rate_for_hotel(hotel, date_str, client)
        rates[hotel]   = rate
        sources[hotel] = source
        if i < len(HOTELS) - 1:
            time.sleep(8)
    return rates, sources


def rate_color(rate_str):
    if not rate_str or rate_str == 'N/A':
        return '#555555'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
        if val >= 100:
            return '#b91c1c'
        if val >= 75:
            return '#92400e'
        return '#14532d'
    except Exception:
        return '#555555'


def rate_bg(rate_str):
    if not rate_str or rate_str == 'N/A':
        return '#f5f5f5'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
        if val >= 100:
            return '#fff1f1'
        if val >= 75:
            return '#fefce8'
        return '#f0fdf4'
    except Exception:
        return '#f5f5f5'


def rate_dot_color(rate_str):
    if not rate_str or rate_str == 'N/A':
        return '#aaaaaa'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
        if val >= 100:
            return '#ef4444'
        if val >= 75:
            return '#f59e0b'
        return '#22c55e'
    except Exception:
        return '#aaaaaa'


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


def get_stat(rates, fn):
    vals = []
    for h in HOTELS:
        r = rates.get(h, 'N/A')
        if r and r != 'N/A':
            try:
                vals.append(int(r.replace('$', '').replace(',', '')))
            except Exception:
                pass
    return '$' + str(fn(vals)) if vals else 'N/A'


def source_badge(source):
    s = (source or 'unknown').lower().strip()
    color_map = {
        'google hotels':   ('#1a73e8', '#ffffff'),
        'google':          ('#1a73e8', '#ffffff'),
        'kayak.com':       ('#ff690f', '#ffffff'),
        'kayak':           ('#ff690f', '#ffffff'),
        'wyndham.com':     ('#004990', '#ffffff'),
        'wyndham':         ('#004990', '#ffffff'),
        'motel6.com':      ('#c8102e', '#ffffff'),
        'motel6':          ('#c8102e', '#ffffff'),
        'redroof.com':     ('#cc0000', '#ffffff'),
        'tripadvisor':     ('#00aa6c', '#ffffff'),
        'tripadvisor.com': ('#00aa6c', '#ffffff'),
        'hotels.com':      ('#d4001f', '#ffffff'),
        'expedia':         ('#1b0077', '#ffffff'),
        'expedia.com':     ('#1b0077', '#ffffff'),
        'booking.com':     ('#003580', '#ffffff'),
        'booking':         ('#003580', '#ffffff'),
    }
    bg, fg = color_map.get(s, ('#555555', '#ffffff'))
    label  = source if source not in ('unknown', 'not found', 'error', 'rate limit', '') else 'unknown'
    return (
        '<span style=font-size:10px;font-weight:700;background:' + bg +
        ';color:' + fg + ';padding:2px 8px;border-radius:10px;display:inline-block;>' + label + '</span>'
    )


def build_email(rates, sources, today_str, events):
    lowest  = get_stat(rates, min)
    highest = get_stat(rates, max)

    # Hotel rows — white background, dark text, high contrast
    hotel_rows = ''
    for i, hotel in enumerate(HOTELS):
        rate     = rates.get(hotel, 'N/A') or 'N/A'
        src      = sources.get(hotel, 'unknown')
        color    = rate_color(rate)
        bg       = rate_bg(rate)
        dot_col  = rate_dot_color(rate)
        badge    = source_badge(src)
        row_border = '2px solid #e5e7eb' if i == len(HOTELS) - 1 else '1px solid #e5e7eb'
        hotel_rows += (
            '<tr style=background:' + bg + ';>'
            '<td style=padding:6px 8px 6px 16px;font-size:13px;color:#6b7280;width:24px;vertical-align:middle;border-bottom:' + row_border + ';>' + str(i+1) + '</td>'
            '<td style=padding:14px 10px;vertical-align:middle;border-bottom:' + row_border + ';>'
            '<div style=display:flex;align-items:flex-start;gap:8px;>'
            '<span style=display:inline-block;width:11px;height:11px;border-radius:50%;background:' + dot_col + ';margin-top:3px;flex-shrink:0;></span>'
            '<div>'
            '<div style=font-size:14px;font-weight:700;color:#111827;margin-bottom:5px;>' + hotel + '</div>'
            + badge +
            '</div></div>'
            '</td>'
            '<td style=padding:14px 16px 14px 10px;text-align:right;vertical-align:middle;border-bottom:' + row_border + ';>'
            '<div style=font-size:28px;font-weight:800;color:' + color + ';line-height:1;>' + rate + '</div>'
            '<div style=font-size:11px;color:#6b7280;margin-top:3px;>per night</div>'
            '</td>'
            '</tr>'
        )

    # Event rows — white background, dark text
    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            if imp == 'HIGH':
                bb, rb = '#b91c1c', '#fff8f8'
                icon   = '🔴'
            elif imp == 'MODERATE':
                bb, rb = '#b45309', '#fffbeb'
                icon   = '🟡'
            else:
                bb, rb = '#15803d', '#f0fdf4'
                icon   = '🟢'
            event_rows += (
                '<tr style=background:' + rb + ';border-bottom:1px solid #e5e7eb;>'
                '<td style=padding:13px 16px;>'
                '<div style=font-size:14px;font-weight:700;color:#111827;margin-bottom:4px;>' + icon + ' ' + ev['name'] + '</div>'
                '<div style=font-size:12px;color:#4b5563;>'
                '📅 ' + fmt_event_date(ev) + ' &nbsp;&bull;&nbsp; 📍 ' + ev['venue'] +
                '</div></td>'
                '<td style=padding:13px 16px;text-align:right;white-space:nowrap;vertical-align:middle;>'
                '<span style=background:' + bb + ';color:#ffffff;font-size:11px;font-weight:700;padding:4px 12px;border-radius:20px;>' + imp + '</span>'
                '</td></tr>'
            )
    else:
        event_rows = '<tr><td colspan=2 style=padding:20px;color:#6b7280;font-size:13px;text-align:center;background:#ffffff;>No major events in the next 60 days.</td></tr>'

    html = (
        '<!DOCTYPE html><html><head><meta charset=UTF-8>'
        '<meta name=viewport content=width=device-width,initial-scale=1></head>'
        '<body style=margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;>'
        '<div style=max-width:600px;margin:20px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.10);>'

        # HEADER — dark bg, white text — good contrast
        '<div style=background:#1b2e1b;padding:28px 28px 24px;>'
        '<div style=font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#86efac;font-weight:600;margin-bottom:6px;>York, Pennsylvania</div>'
        '<div style=font-size:26px;font-weight:800;color:#ffffff;margin-bottom:14px;>🏨 Hotel Rate Monitor</div>'
        '<div style=background:rgba(255,255,255,0.12);border-radius:8px;padding:9px 14px;display:inline-block;>'
        '<span style=font-size:12px;color:#d1fae5;font-weight:500;>📅 ' + fmt_date(today_str) + ' &nbsp;&bull;&nbsp; ☀️ Daily 7 AM Report</span>'
        '</div></div>'

        # STAT BAR — medium dark bg, white/bright text
        '<div style=background:#2d4a2d;display:flex;border-bottom:3px solid #1b2e1b;>'
        '<div style=flex:1;padding:16px 8px;text-align:center;border-right:1px solid rgba(255,255,255,0.15);>'
        '<div style=font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#86efac;margin-bottom:5px;font-weight:600;>Lowest Tonight</div>'
        '<div style=font-size:28px;font-weight:800;color:#ffffff;>' + lowest + '</div>'
        '</div>'
        '<div style=flex:1;padding:16px 8px;text-align:center;border-right:1px solid rgba(255,255,255,0.15);>'
        '<div style=font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#86efac;margin-bottom:5px;font-weight:600;>Highest Tonight</div>'
        '<div style=font-size:28px;font-weight:800;color:#ffffff;>' + highest + '</div>'
        '</div>'
        '<div style=flex:1;padding:16px 8px;text-align:center;>'
        '<div style=font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#86efac;margin-bottom:5px;font-weight:600;>Tracked</div>'
        '<div style=font-size:28px;font-weight:800;color:#ffffff;>7</div>'
        '</div></div>'

        # RATES HEADER — white bg, dark text
        '<div style=padding:20px 24px 12px;background:#ffffff;>'
        '<div style=display:flex;align-items:center;gap:10px;>'
        '<div style=width:4px;height:22px;background:#1b2e1b;border-radius:2px;flex-shrink:0;></div>'
        '<div>'
        '<div style=font-size:14px;font-weight:700;color:#111827;letter-spacing:0.5px;text-transform:uppercase;>Tonight\'s Rates</div>'
        '<div style=font-size:12px;color:#6b7280;margin-top:2px;>' + fmt_date(today_str) + '</div>'
        '</div></div></div>'

        '<table width=100% cellpadding=0 cellspacing=0 style=background:#ffffff;>'
        '<tbody>' + hotel_rows + '</tbody></table>'

        # LEGEND — white bg, dark text
        '<div style=padding:10px 24px;background:#f9fafb;border-top:1px solid #e5e7eb;border-bottom:2px solid #e5e7eb;>'
        '<span style=font-size:12px;color:#374151;font-weight:500;>'
        '<span style=display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e;margin-right:5px;vertical-align:middle;></span>Under $75 &nbsp;&nbsp;'
        '<span style=display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-right:5px;vertical-align:middle;></span>$75–$99 &nbsp;&nbsp;'
        '<span style=display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;margin-right:5px;vertical-align:middle;></span>$100+'
        '</span></div>'

        # EVENTS HEADER
        '<div style=padding:20px 24px 12px;background:#ffffff;>'
        '<div style=display:flex;align-items:center;gap:10px;>'
        '<div style=width:4px;height:22px;background:#d97706;border-radius:2px;flex-shrink:0;></div>'
        '<div>'
        '<div style=font-size:14px;font-weight:700;color:#111827;letter-spacing:0.5px;text-transform:uppercase;>York PA Events</div>'
        '<div style=font-size:12px;color:#6b7280;margin-top:2px;>Upcoming in the next 60 days</div>'
        '</div></div></div>'

        '<div style=margin:0 16px 24px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;>'
        '<table width=100% cellpadding=0 cellspacing=0><tbody>' + event_rows + '</tbody></table>'
        '</div>'

        # FOOTER — dark bg, readable text
        '<div style=background:#1b2e1b;padding:18px 24px;text-align:center;>'
        '<div style=font-size:12px;color:#86efac;font-weight:700;margin-bottom:5px;letter-spacing:1px;>YORK PA HOTEL RATE MONITOR</div>'
        '<div style=font-size:11px;color:#6ee7b7;line-height:1.8;>'
        'Ramada &bull; Inn at York &bull; Motel 6 (x2) &bull; Red Roof &bull; Days Inn &bull; Quality Inn<br>'
        'Sent daily at 7:00 AM ET'
        '</div></div>'

        '</div></body></html>'
    )
    return html


def send_email(html, today_str):
    dt      = datetime.strptime(today_str, '%Y-%m-%d')
    subject = '🏨 York PA Hotel Rates — ' + dt.strftime('%A, %B ') + str(dt.day) + ', ' + str(dt.year)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = SENDER_EMAIL
    msg['To']      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print('Email sent: ' + subject)
    except Exception as e:
        print('Email failed: ' + str(e))
        raise


def main():
    print('York PA Hotel Rate Monitor starting...')
    today_str = get_today()
    print('Today: ' + today_str)
    rates, sources = fetch_all_rates(today_str)
    events = get_events()
    print('Events: ' + str(len(events)))
    html = build_email(rates, sources, today_str, events)
    send_email(html, today_str)
    print('Done!')


if __name__ == '__main__':
    main()
