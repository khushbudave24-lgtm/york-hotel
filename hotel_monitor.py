import anthropic
import smtplib
import os
import json
import re
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


def get_dates():
    et    = pytz.timezone(TIMEZONE)
    today = datetime.now(et).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday   = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    return str(today), str(next_friday), str(next_saturday)


def fetch_rates_claude(date_str, label, retries=3):
    dt_obj      = datetime.strptime(date_str, '%Y-%m-%d')
    date_pretty = dt_obj.strftime('%B %d, %Y')

    # Short focused prompt to minimize tokens
    prompt = (
        'Find the lowest room rate in USD on booking.com for each hotel in York PA for ' + date_pretty + '. '
        'If not on booking.com use expedia.com. Search each hotel by name.\n\n'
        'Hotels:\n'
        '1. Ramada by Wyndham York PA\n'
        '2. Inn at York PA\n'
        '3. Motel 6 York PA\n'
        '4. Motel 6 North York PA\n'
        '5. Red Roof Inn York PA\n'
        '6. Days Inn York PA\n'
        '7. Quality Inn and Suites York East PA\n\n'
        'Reply with ONLY this JSON, nothing else:\n'
        '{"Ramada by Wyndham York PA":"$XX","Inn at York PA":"$XX","Motel 6 York PA":"$XX",'
        '"Motel 6 North York PA":"$XX","Red Roof Inn York PA":"$XX","Days Inn York PA":"$XX",'
        '"Quality Inn and Suites York East PA":"$XX"}\n'
        'Use "N/A" if unavailable.'
    )

    for attempt in range(retries):
        try:
            client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model      = 'claude-sonnet-4-5',
                max_tokens = 512,
                tools      = [{'type': 'web_search_20250305', 'name': 'web_search'}],
                messages   = [{'role': 'user', 'content': prompt}],
            )
            full_text = ''
            for block in response.content:
                if hasattr(block, 'text'):
                    full_text += block.text

            print(label + ' raw: ' + full_text[:200])

            start = full_text.find('{')
            end   = full_text.rfind('}') + 1
            if start >= 0 and end > start:
                rates = json.loads(full_text[start:end])
                for h in HOTELS:
                    print('  ' + h + ': ' + rates.get(h, 'N/A'))
                return rates
            print(label + ' no JSON, attempt ' + str(attempt + 1))

        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(label + ' rate limit, waiting ' + str(wait) + 's...')
            time.sleep(wait)
        except Exception as e:
            print(label + ' error: ' + str(e)[:100])
            if attempt < retries - 1:
                time.sleep(30)

    return {}


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
    return dt.strftime('%A, %B ') + str(dt.day)


def fmt_date_short(d):
    dt = datetime.strptime(d, '%Y-%m-%d')
    return dt.strftime('%b ') + str(dt.day)


def fmt_event_date(ev):
    s = datetime.strptime(ev['start'], '%Y-%m-%d')
    e = datetime.strptime(ev['end'],   '%Y-%m-%d')
    if ev['start'] == ev['end']:
        return s.strftime('%b ') + str(s.day)
    if s.month == e.month:
        return s.strftime('%b ') + str(s.day) + '-' + str(e.day)
    return s.strftime('%b ') + str(s.day) + ' - ' + e.strftime('%b ') + str(e.day)


def get_stat(rates_dict, fn):
    vals = []
    for h in HOTELS:
        r = rates_dict.get(h, 'N/A')
        if r and r != 'N/A':
            try:
                vals.append(int(r.replace('$', '').replace(',', '')))
            except Exception:
                pass
    return '$' + str(fn(vals)) if vals else 'N/A'


def build_hotel_table(rates, show_number=True):
    rows = ''
    for i, hotel in enumerate(HOTELS):
        rate  = rates.get(hotel, 'N/A') or 'N/A'
        color = rate_color(rate)
        bg    = rate_bg(rate)
        dot   = '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:' + color + ';margin-right:8px;vertical-align:middle;></span>'
        num   = ('<td style=padding:14px 6px 14px 20px;font-size:12px;color:#9ca3af;width:20px;vertical-align:middle;>' + str(i+1) + '</td>') if show_number else '<td style=width:0px;></td>'
        rows += (
            '<tr style=background:' + bg + ';border-bottom:1px solid #f3f4f6;>'
            + num
            + '<td style=padding:14px 10px;font-size:13px;font-weight:600;color:#1f2937;vertical-align:middle;>' + dot + hotel + '</td>'
            + '<td style=padding:14px 20px 14px 10px;text-align:right;vertical-align:middle;>'
            + '<span style=font-size:22px;font-weight:800;color:' + color + ';>' + rate + '</span>'
            + '</td>'
            + '</tr>'
        )
    return rows


def build_email(today_rates, friday_rates, saturday_rates, dates, events, send_time_str):
    today_str, friday_str, saturday_str = dates
    lowest_today  = get_stat(today_rates,    min)
    highest_today = get_stat(today_rates,    max)
    lowest_fri    = get_stat(friday_rates,   min)
    lowest_sat    = get_stat(saturday_rates, min)

    today_rows    = build_hotel_table(today_rates)
    friday_rows   = build_hotel_table(friday_rates,   show_number=False)
    saturday_rows = build_hotel_table(saturday_rates, show_number=False)

    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            if imp == 'HIGH':
                badge_bg = '#dc2626'
                row_bg   = '#fff7f7'
            elif imp == 'MODERATE':
                badge_bg = '#d97706'
                row_bg   = '#fffdf0'
            else:
                badge_bg = '#16a34a'
                row_bg   = '#f0fdf4'
            event_rows += (
                '<tr style=background:' + row_bg + ';border-bottom:1px solid #f3f4f6;>'
                '<td style=padding:12px 20px;>'
                '<div style=font-size:13px;font-weight:700;color:#1f2937;>' + ev['name'] + '</div>'
                '<div style=font-size:11px;color:#6b7280;margin-top:2px;>' + fmt_event_date(ev) + ' &bull; ' + ev['venue'] + '</div>'
                '</td>'
                '<td style=padding:12px 20px;text-align:right;>'
                '<span style=background:' + badge_bg + ';color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;>' + imp + '</span>'
                '</td>'
                '</tr>'
            )
    else:
        event_rows = '<tr><td colspan=2 style=padding:16px 20px;color:#9ca3af;font-size:13px;text-align:center;>No major events in the next 60 days.</td></tr>'

    html = (
        '<!DOCTYPE html><html><head><meta charset=UTF-8>'
        '<meta name=viewport content=width=device-width,initial-scale=1></head>'
        '<body style=margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;>'
        '<div style=max-width:620px;margin:24px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);>'

        # HEADER
        '<div style=background:linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%);padding:36px 32px 28px;>'
        '<div style=margin-bottom:16px;>'
        '<div style=font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#7dd3fc;font-weight:600;margin-bottom:4px;>York, Pennsylvania</div>'
        '<div style=font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;>🏨 Hotel Rate Monitor</div>'
        '</div>'
        '<div style=font-size:12px;color:#93c5fd;background:rgba(255,255,255,0.08);border-radius:8px;padding:8px 14px;display:inline-block;>'
        '📅 ' + fmt_date(today_str) + ' &nbsp;&bull;&nbsp; 🕐 ' + send_time_str + ' ET'
        '</div></div>'

        # STAT BAR
        '<div style=background:#1e3a5f;display:flex;>'
        '<div style=flex:1;padding:16px;text-align:center;border-right:1px solid rgba(255,255,255,0.08);>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:4px;>Lowest Tonight</div>'
        '<div style=font-size:26px;font-weight:800;color:#34d399;>' + lowest_today + '</div>'
        '</div>'
        '<div style=flex:1;padding:16px;text-align:center;border-right:1px solid rgba(255,255,255,0.08);>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:4px;>Highest Tonight</div>'
        '<div style=font-size:26px;font-weight:800;color:#f87171;>' + highest_today + '</div>'
        '</div>'
        '<div style=flex:1;padding:16px;text-align:center;>'
        '<div style=font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#60a5fa;margin-bottom:4px;>Properties</div>'
        '<div style=font-size:26px;font-weight:800;color:#ffffff;>7</div>'
        '</div></div>'

        # TODAY SECTION HEADER
        '<div style=padding:22px 28px 10px;>'
        '<div style=display:flex;align-items:center;margin-bottom:4px;>'
        '<div style=width:4px;height:20px;background:linear-gradient(180deg,#3b82f6,#1d4ed8);border-radius:2px;margin-right:12px;></div>'
        '<div style=font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#374151;>Tonight\'s Rates &mdash; ' + fmt_date(today_str) + '</div>'
        '</div></div>'
        '<table width=100% cellpadding=0 cellspacing=0 style=border-top:1px solid #f3f4f6;>'
        '<tbody>' + today_rows + '</tbody></table>'

        # LEGEND
        '<div style=padding:10px 20px;background:#f8fafc;border-top:1px solid #f3f4f6;>'
        '<span style=font-size:11px;color:#6b7280;>'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#16a34a;margin-right:4px;></span>Under $75 &nbsp;&nbsp;'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#d97706;margin-right:4px;></span>$75-$99 &nbsp;&nbsp;'
        '<span style=display:inline-block;width:8px;height:8px;border-radius:50%;background:#dc2626;margin-right:4px;></span>$100+'
        '</span></div>'

        # WEEKEND HEADER
        '<div style=padding:22px 28px 12px;>'
        '<div style=display:flex;align-items:center;>'
        '<div style=width:4px;height:20px;background:linear-gradient(180deg,#8b5cf6,#6d28d9);border-radius:2px;margin-right:12px;></div>'
        '<div style=font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#374151;>Upcoming Weekend Rates</div>'
        '</div></div>'

        # FRIDAY BOX
        '<div style=margin:0 20px 12px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;>'
        '<div style=background:linear-gradient(135deg,#7c3aed,#5b21b6);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;>'
        '<div style=font-size:13px;font-weight:700;color:#ffffff;>📅 Friday &mdash; ' + fmt_date_short(friday_str) + '</div>'
        '<div style=font-size:11px;color:#c4b5fd;background:rgba(255,255,255,0.15);padding:3px 10px;border-radius:20px;>From ' + lowest_fri + '</div>'
        '</div>'
        '<table width=100% cellpadding=0 cellspacing=0><tbody>' + friday_rows + '</tbody></table>'
        '</div>'

        # SATURDAY BOX
        '<div style=margin:0 20px 20px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;>'
        '<div style=background:linear-gradient(135deg,#0369a1,#0c4a6e);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;>'
        '<div style=font-size:13px;font-weight:700;color:#ffffff;>🏙️ Saturday &mdash; ' + fmt_date_short(saturday_str) + '</div>'
        '<div style=font-size:11px;color:#bae6fd;background:rgba(255,255,255,0.15);padding:3px 10px;border-radius:20px;>From ' + lowest_sat + '</div>'
        '</div>'
        '<table width=100% cellpadding=0 cellspacing=0><tbody>' + saturday_rows + '</tbody></table>'
        '</div>'

        # EVENTS HEADER
        '<div style=padding:22px 28px 12px;>'
        '<div style=display:flex;align-items:center;>'
        '<div style=width:4px;height:20px;background:linear-gradient(180deg,#f59e0b,#d97706);border-radius:2px;margin-right:12px;></div>'
        '<div style=font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#374151;>York PA Events &mdash; Next 60 Days</div>'
        '</div></div>'

        # EVENTS BOX
        '<div style=margin:0 20px 24px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;>'
        '<table width=100% cellpadding=0 cellspacing=0><tbody>' + event_rows + '</tbody></table>'
        '</div>'

        # FOOTER
        '<div style=background:#0f2027;padding:20px 32px;text-align:center;>'
        '<div style=font-size:12px;color:#60a5fa;font-weight:600;margin-bottom:6px;>York PA Hotel Rate Monitor</div>'
        '<div style=font-size:11px;color:#475569;line-height:1.8;>'
        'Ramada &bull; Inn at York &bull; Motel 6 (x2) &bull; Red Roof &bull; Days Inn &bull; Quality Inn<br>'
        'Delivered to khushbudave24@gmail.com &bull; Powered by Claude AI + Booking.com'
        '</div></div>'

        '</div></body></html>'
    )
    return html


def send_email(html_content, today_str, send_time_str):
    dt      = datetime.strptime(today_str, '%Y-%m-%d')
    subject = '🏨 York PA Hotel Rates — ' + dt.strftime('%b ') + str(dt.day) + ' @ ' + send_time_str + ' ET'
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = SENDER_EMAIL
    msg['To']      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))
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
    et            = pytz.timezone(TIMEZONE)
    now           = datetime.now(et)
    send_time_str = now.strftime('%I:%M %p').lstrip('0')
    dates = get_dates()
    today_str, friday_str, saturday_str = dates
    print('Dates: ' + today_str + ' | Fri: ' + friday_str + ' | Sat: ' + saturday_str)

    print('Fetching today rates...')
    today_rates = fetch_rates_claude(today_str, 'TODAY')

    print('Waiting 90 seconds before next call...')
    time.sleep(90)

    print('Fetching Friday rates...')
    friday_rates = fetch_rates_claude(friday_str, 'FRIDAY')

    print('Waiting 90 seconds before next call...')
    time.sleep(90)

    print('Fetching Saturday rates...')
    saturday_rates = fetch_rates_claude(saturday_str, 'SATURDAY')

    events = get_events()
    print('Events: ' + str(len(events)))

    html = build_email(today_rates, friday_rates, saturday_rates, dates, events, send_time_str)
    send_email(html, today_str, send_time_str)
    print('Done!')


if __name__ == '__main__':
    main()
