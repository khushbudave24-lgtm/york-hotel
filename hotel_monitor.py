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
        'Use your web search tool to search Google for: '
        '"' + hotel_name + ' York PA hotel room price ' + date_pretty + '"\n\n'
        'Look at the search results and find the room rate shown in Google search results, '
        'Google Hotels panel, or any travel website that appears in results.\n\n'
        'Return ONLY this JSON with no other text:\n'
        '{"rate": "$XX", "source": "website name"}\n\n'
        'Rules:\n'
        '- rate: the lowest room price found as a dollar amount like "$79"\n'
        '- source: the website name where you found it like "google hotels", "wyndham.com", "tripadvisor.com"\n'
        '- If no price found use: {"rate": "N/A", "source": "not found"}'
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

        print('  ' + hotel_name + ': no JSON — ' + full_text[:80])
        return 'N/A', 'not found'

    except anthropic.RateLimitError:
        print('  ' + hotel_name + ': rate limit, waiting 60s')
        time.sleep(60)
        return 'N/A', 'rate limit'
    except Exception as e:
        print('  ' + hotel_name + ': error ' + str(e)[:80])
        return 'N/A', 'error'


def fetch_all_rates(date_str):
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    rates   = {}
    sources = {}
    for i, hotel in enumerate(HOTELS):
        rate, source      = fetch_rate_for_hotel(hotel, date_str, client)
        rates[hotel]      = rate
        sources[hotel]    = source
        if i < len(HOTELS) - 1:
            time.sleep(8)
    return rates, sources


def rate_color(rate_str):
    if not rate_str or rate_str == 'N/A':
        return '#9ca3af'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
        if val >= 100:
            return '#dc2626'
        if val >= 75:
            return '#d97706'
        return '#16a34a'
    except Exception:
        return '#9ca3af'


def rate_bg(rate_str):
    if not rate_str or rate_str == 'N/A':
        return '#f9fafb'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
        if val >= 100:
            return '#fef2f2'
        if val >= 75:
            return '#fffbeb'
        return '#f0fdf4'
    except Exception:
        return '#f9fafb'


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
        'google hotels':    ('#1a73e8', '#e8f0fe'),
        'google':           ('#1a73e8', '#e8f0fe'),
        'wyndham.com':      ('#004990', '#dce8f5'),
        'wyndham':          ('#004990', '#dce8f5'),
        'innatyork.com':    ('#6b4c3b', '#f5ede8'),
        'motel6.com':       ('#c8102e', '#fde8eb'),
        'motel6':           ('#c8102e', '#fde8eb'),
        'redroof.com':      ('#cc0000', '#fde8e8'),
        'redroof':          ('#cc0000', '#fde8e8'),
        'tripadvisor':      ('#00aa6c', '#e0f5ee'),
        'tripadvisor.com':  ('#00aa6c', '#e0f5ee'),
        'hotels.com':       ('#c00', '#ffe0e0'),
        'expedia':          ('#1b0077', '#ede8ff'),
        'expedia.com':      ('#1b0077', '#ede8ff'),
        'booking.com':      ('#003580', '#d4e6ff'),
        'booking':          ('#003580', '#d4e6ff'),
    }
    bg, fg = color_map.get(s, ('#6b7280', '#f3f4f6'))
    label  = source if source not in ('unknown', 'not found', 'error', 'rate limit') else '—'
    return (
        '<span style=font-size:10px;font-weight:700;background:' + bg +
        ';color:' + fg + ';padding:2px 8px;border-radius:10px;>' + label + '</span>'
    )


def build_email(rates, sources, today_str, events):
    lowest  = get_stat(rates, min)
    highest = get_stat(rates, max)

    hotel_rows = ''
    for i, hotel in enumerate(HOTELS):
        rate  = rates.get(hotel, 'N/A') or 'N/A'
        src   = sources.get(hotel, 'unknown')
        color = rate_color(rate)
        bg    = rate_bg(rate)
        dot   = '<span style=display:inline-block;width:10px;height:10px;border-radius:50%;background:' + color + ';margin-right:8px;flex-shrink:0;></span>'
        badge = source_badge(src)
        hotel_rows += (
            '<tr style=background:' + bg + ';border-bottom:1px solid #f3f4f6;>'
            '<td style=padding:4px 6px 4px 16px;font-size:12px;color:#9ca3af;width:22px;vertical-align:middle;>' + str(i+1) + '</td>'
            '<td style=padding:13px 10px;vertical-align:middle;>'
            '<div style=display:flex;align-items:center;>' + dot +
            '<div>'
            '<div style=font-size:13px;font-weight:600;color:#1f2937;margin-bottom:4px;>' + hotel + '</div>'
            + badge +
            '</div></div>'
            '</td>'
            '<td style=padding:13px 16px 13px 10px;text-align:right;vertical-align:middle;white-space:nowrap;>'
            '<div style=font-size:26px;font-weight:800;color:' + color + ';line-height:1;>' + rate + '</div>'
            '<div style=font-size:10px;color:#9ca3af;margin-top:3px;>per night</div>'
            '</td>'
            '</tr>'
        )

    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            if imp == 'HIGH':
                bb, rb, ic = '#dc2626', '#fff7f7', '🔴'
            elif imp == 'MODERATE':
                bb, rb, ic = '#d97706', '#fffdf0', '🟡'
            else:
                bb, rb, ic = '#16a34a', '#f0fdf4', '🟢'
            event_rows += (
                '<tr style=background:' + rb + ';border-bottom:1px solid #f3f4f6;>'
                '<td style=padding:12px 16px;>'
                '<div style=font-size:13px;font-weight:700;color:#1f2937;>' + ic + ' ' + ev['name'] + '</div>'
                '<div style=font-size:11px;color:#6b7280;margin-top:3px;>'
                '📅 ' + fmt_event_date(ev) + ' &nbsp;&bull;&nbsp; 📍 ' + ev['venue'] +
                '</div></td>'
                '<td style=padding:12px 16px;text-align:right;white-space:nowrap;>'
                '<span style=background:' + bb + ';color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;>' + imp + '</span>'
                '</td></tr>'
            )
    else:
        event_rows = '<tr><td colspan=2 style=padding:20px;color:#9ca3af;font-size:13px;text-align:center;>No major events in the next 60 days.</td></tr>'

    html = (
        '<!DOCTYPE html><html><head><meta charset=UTF-8>'
        '<meta name=viewport content=width=device-width,initial-scale=1></head>'
        '<body style=margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;>'
        '<div style=max-width:620px;margin:24px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.12);>'

        '<div style=background:linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%);padding:32px;>'
        '<div style=font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#7dd3fc;font-weight:600;margin-bottom:6px;>🏙️ York, Pennsylvania</div>'
        '<div style=font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;margin-bottom:14px;>Hotel Rate Monitor</div>'
        '<div style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:10px;padding:10px 16px;display:inline-block;>'
        '<span style=font-size:12px;color:#bfdbfe;>📅 ' + fmt_date(today_str) + ' &nbsp;&bull;&nbsp; ☀️ Daily 7 AM Report</span>'
        '</div></div>'

        '<div style=background:#1e3a5f;display:flex;>'
        '<div style=flex:1;padding:18px 12px;text-align:center;border-right:1px solid rgba(255,255,255,0.08);>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:6px;>Lowest Tonight</div>'
        '<div style=font-size:28px;font-weight:800;color:#34d399;>' + lowest + '</div>'
        '</div>'
        '<div style=flex:1;padding:18px 12px;text-align:center;border-right:1px solid rgba(255,255,255,0.08);>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:6px;>Highest Tonight</div>'
        '<div style=font-size:28px;font-weight:800;color:#f87171;>' + highest + '</div>'
        '</div>'
        '<div style=flex:1;padding:18px 12px;text-align:center;>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:6px;>Hotels Tracked</div>'
        '<div style=font-size:28px;font-weight:800;color:#ffffff;>7</div>'
        '</div></div>'

        '<div style=padding:20px 20px 10px;display:flex;align-items:center;>'
        '<div style=width:4px;height:22px;background:linear-gradient(180deg,#3b82f6,#1d4ed8);border-radius:2px;margin-right:12px;flex-shrink:0;></div>'
        '<div>'
        '<div style=font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#374151;>Tonight\'s Rates</div>'
        '<div style=font-size:11px;color:#9ca3af;margin-top:2px;>Sourced via Google search &amp; hotel websites</div>'
        '</div></div>'

        '<table width=100% cellpadding=0 cellspacing=0 style=border-top:2px solid #f3f4f6;>'
        '<tbody>' + hotel_rows + '</tbody></table>'

        '<div style=padding:10px 16px;background:#f8fafc;border-top:1px solid #f3f4f6;border-bottom:2px solid #e5e7eb;>'
        '<span style=font-size:11px;color:#6b7280;>'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#16a34a;margin-right:4px;></span>Under $75 &nbsp;'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#d97706;margin-right:4px;></span>$75–$99 &nbsp;'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#dc2626;margin-right:4px;></span>$100+'
        '</span></div>'

        '<div style=padding:20px 20px 10px;display:flex;align-items:center;>'
        '<div style=width:4px;height:22px;background:linear-gradient(180deg,#f59e0b,#d97706);border-radius:2px;margin-right:12px;flex-shrink:0;></div>'
        '<div>'
        '<div style=font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#374151;>York PA Events</div>'
        '<div style=font-size:11px;color:#9ca3af;margin-top:2px;>Upcoming in the next 60 days</div>'
        '</div></div>'

        '<div style=margin:0 16px 24px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;>'
        '<table width=100% cellpadding=0 cellspacing=0><tbody>' + event_rows + '</tbody></table>'
        '</div>'

        '<div style=background:linear-gradient(135deg,#0f2027,#1a3a4a);padding:20px 24px;text-align:center;>'
        '<div style=font-size:12px;color:#60a5fa;font-weight:700;margin-bottom:6px;letter-spacing:1px;>YORK PA HOTEL RATE MONITOR</div>'
        '<div style=font-size:11px;color:#475569;line-height:1.8;>'
        'Ramada &bull; Inn at York &bull; Motel 6 (x2) &bull; Red Roof &bull; Days Inn &bull; Quality Inn<br>'
        'Sent daily at 7:00 AM ET &bull; Powered by Claude AI'
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
    print('Fetching rates one hotel at a time...')
    rates, sources = fetch_all_rates(today_str)
    events = get_events()
    print('Events: ' + str(len(events)))
    html = build_email(rates, sources, today_str, events)
    send_email(html, today_str)
    print('Done!')


if __name__ == '__main__':
    main()
