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
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = 'khushbudave24@gmail.com'
TIMEZONE = 'America/New_York'

HOTELS = [
    'Ramada by Wyndham York PA',
    'Inn at York PA',
    'Motel 6 York PA',
    'Motel 6 North York PA',
    'Red Roof Inn York PA',
    'Days Inn York PA',
    'Quality Inn and Suites York East PA',
]

EVENTS_PROMPT = '''Search for upcoming events in York Pennsylvania in the next 30 days that would cause hotel rate increases.
Return a JSON array only, no other text, like this:
[{"name": "Event Name", "date": "Date range", "venue": "Venue name", "impact": "HIGH or MODERATE or LOW"}]
If no events found return an empty array [].'''


def get_dates():
    et = pytz.timezone(TIMEZONE)
    today = datetime.now(et).date()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    return str(today), str(next_friday), str(next_saturday)


def fetch_rates_with_claude(date_str):
    et = pytz.timezone(TIMEZONE)
    date_display = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')

    prompt = '''Search the web for hotel room rates for the following hotels in York Pennsylvania for ''' + date_display + '''.
For each hotel find the lowest available room rate in USD from the hotel official website, Expedia, Hotels.com, or Google Hotels.

Hotels to search:
1. Ramada by Wyndham York PA
2. Inn at York PA
3. Motel 6 York PA (South George Street)
4. Motel 6 North York PA (North George Street)
5. Red Roof Inn York PA
6. Days Inn York PA
7. Quality Inn and Suites York East PA

Return ONLY a valid JSON object, no other text, in this exact format:
{
  "Ramada by Wyndham York PA": "$XX",
  "Inn at York PA": "$XX",
  "Motel 6 York PA": "$XX",
  "Motel 6 North York PA": "$XX",
  "Red Roof Inn York PA": "$XX",
  "Days Inn York PA": "$XX",
  "Quality Inn and Suites York East PA": "$XX"
}
If a rate is not found use "N/A". Use whole dollar amounts only like "$75".'''

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            tools=[{'type': 'web_search_20250305', 'name': 'web_search'}],
            messages=[{'role': 'user', 'content': prompt}]
        )

        full_text = ''
        for block in response.content:
            if block.type == 'text':
                full_text += block.text

        print('Claude response for ' + date_str + ':')
        print(full_text[:500])

        start = full_text.find('{')
        end = full_text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = full_text[start:end]
            rates = json.loads(json_str)
            return rates
        return {}

    except Exception as e:
        print('Claude error for ' + date_str + ': ' + str(e))
        return {}


def fetch_events_with_claude():
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            tools=[{'type': 'web_search_20250305', 'name': 'web_search'}],
            messages=[{'role': 'user', 'content': EVENTS_PROMPT}]
        )

        full_text = ''
        for block in response.content:
            if block.type == 'text':
                full_text += block.text

        print('Events response: ' + full_text[:300])

        start = full_text.find('[')
        end = full_text.rfind(']') + 1
        if start >= 0 and end > start:
            return json.loads(full_text[start:end])
        return []

    except Exception as e:
        print('Events error: ' + str(e))
        return []


def rate_color(rate_str):
    if rate_str == 'N/A':
        return '#888888'
    try:
        val = int(rate_str.replace('$', '').replace(',', ''))
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
    vals = []
    for h in HOTELS:
        r = rates.get(h, 'N/A')
        if r != 'N/A':
            try:
                vals.append(int(r.replace('$', '').replace(',', '')))
            except Exception:
                pass
    return '$' + str(min(vals)) if vals else 'N/A'


def get_highest(rates):
    vals = []
    for h in HOTELS:
        r = rates.get(h, 'N/A')
        if r != 'N/A':
            try:
                vals.append(int(r.replace('$', '').replace(',', '')))
            except Exception:
                pass
    return '$' + str(max(vals)) if vals else 'N/A'


def build_rows(rates, numbered):
    rows = ''
    for i, hotel in enumerate(HOTELS):
        rate = rates.get(hotel, 'N/A')
        color = rate_color(rate)
        rows += '<tr>'
        if numbered:
            rows += '<td style=padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;color:#555;width:24px;>' + str(i + 1) + '.</td>'
        rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;font-size:13px;font-weight:600;color:#1a1a1a;>' + hotel + '</td>'
        rows += '<td style=padding:10px 8px;border-bottom:1px solid #f0ece3;text-align:right;font-size:18px;font-weight:700;color:' + color + ';>' + rate + '</td>'
        rows += '</tr>'
    return rows


def build_email(all_rates, dates, events):
    today_str, friday_str, saturday_str = dates
    et = pytz.timezone(TIMEZONE)
    now = datetime.now(et)
    send_time = now.strftime('%B ') + str(now.day) + ', ' + str(now.year) + ' at 7:00 AM ET'
    today_rates = all_rates.get(today_str, {})
    friday_rates = all_rates.get(friday_str, {})
    saturday_rates = all_rates.get(saturday_str, {})
    today_rows = build_rows(today_rates, True)
    friday_rows = build_rows(friday_rates, False)
    saturday_rows = build_rows(saturday_rates, False)
    lowest_tonight = get_lowest(today_rates)
    highest_tonight = get_highest(today_rates)

    event_rows = ''
    if events:
        for ev in events:
            imp = ev.get('impact', 'LOW')
            imp_color = '#c0392b' if imp == 'HIGH' else '#e07800' if imp == 'MODERATE' else '#2a7a2a'
            event_rows += '<tr><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;>'
            event_rows += '<span style=font-size:13px;font-weight:600;color:#1b2e1b;>' + ev.get('name', '') + '</span><br>'
            event_rows += '<span style=font-size:11px;color:#999;>' + ev.get('date', '') + ' - ' + ev.get('venue', '') + '</span>'
            event_rows += '</td><td style=padding:11px 8px;border-bottom:1px solid #f0ece3;text-align:right;>'
            event_rows += '<span style=background:' + imp_color + ';color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;>' + imp + '</span>'
            event_rows += '</td></tr>'
    else:
        event_rows = '<tr><td colspan=2 style=padding:14px 8px;color:#888;font-size:13px;>No major events detected this month.</td></tr>'

    html = '<!DOCTYPE html><html><head><meta charset=UTF-8></head><body style=margin:0;padding:20px;background:#edeae3;font-family:Arial,sans-serif;>'
    html += '<div style=max-width:640px;margin:0 auto;background:#ffffff;border-radius:3px;overflow:hidden;box-shadow:0 4px 30px rgba(0,0,0,0.12);>'
    html += '<div style=background:#1b2e1b;padding:32px 36px;>'
    html += '<div style=font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#7eab6e;margin-bottom:8px;font-weight:600;>York, Pennsylvania - Daily Rate Report</div>'
    html += '<div style=font-size:26px;font-weight:700;color:#ffffff;margin-bottom:4px;>Hotel Rate Alert</div>'
    html += '<div style=font-size:12px;color:#9ab890;margin-bottom:16px;>Your 7:00 AM briefing - ' + send_time + '</div>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>Today + Weekend</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;>7 Properties</span>'
    html += '<span style=background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;>Live Rates via AI Search</span>'
    html += '</div>'
    html += '<table width=100% cellpadding=0 cellspacing=0 style=background:#1b2e1b;><tr>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + lowest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Lowest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);><div style=font-size:22px;font-weight:700;color:#ffffff;>' + highest_tonight + '</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Highest Tonight</div></td>'
    html += '<td width=33% style=padding:14px 10px;text-align:center;><div style=font-size:22px;font-weight:700;color:#ffffff;>7 Hotels</div><div style=font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;>Tracked Tonight</div></td>'
    html += '</tr></table>'
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
    html += '<div style=background:#1b2e1b;padding:18px 36px;text-align:center;><p style=font-size:11px;color:#5e8a5e;margin:0;line-height:1.8;>York PA Hotel Rate Alert - Sent daily at 7:00 AM ET<br>Rates sourced via AI web search from hotel and travel websites<br>Delivered to: khushbudave24@gmail.com</p></div>'
    html += '</div></body></html>'
    return html


def send_email(html_content, dates):
    today_str = dates[0]
    dt = datetime.strptime(today_str, '%Y-%m-%d')
    subject = 'York PA Hotel Rates - ' + dt.strftime('%B ') + str(dt.day) + ', ' + str(dt.year)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print('Email sent successfully to ' + RECIPIENT_EMAIL)
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
        print('Fetching rates for: ' + date)
        rates = fetch_rates_with_claude(date)
        all_rates[date] = rates
        for h in HOTELS:
            print('  ' + h + ': ' + rates.get(h, 'N/A'))
        time.sleep(3)

    print('Fetching York PA events...')
    events = fetch_events_with_claude()
    print('Found ' + str(len(events)) + ' events')

    print('Building and sending email...')
    html = build_email(all_rates, dates, events)
    send_email(html, dates)
    print('Done!')


if __name__ == '__main__':
    main()
