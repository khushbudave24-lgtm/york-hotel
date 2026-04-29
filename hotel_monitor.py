import requests
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz
import os

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = "khushbudave24@gmail.com"
TIMEZONE = "America/New_York"

HOTELS = [
{“name”: “Ramada York PA”, “booking_id”: “102097”, “display”: “Ramada by Wyndham York”},
{“name”: “Inn At York PA”, “booking_id”: “91785”, “display”: “Inn at York”},
{“name”: “Motel 6 York PA”, “booking_id”: “127494”, “display”: “Motel 6 York PA”},
{“name”: “Motel 6 North York PA”, “booking_id”: “564194”, “display”: “Motel 6 North York PA”},
{“name”: “Red Roof York PA”, “booking_id”: “687”, “display”: “Red Roof Inn York Downtown”},
{“name”: “Days Inn York PA”, “booking_id”: “274141”, “display”: “Days Inn and Suites York”},
{“name”: “Quality Inn York East”, “booking_id”: “102098”, “display”: “Quality Inn and Suites York East”},
]

def get_events():
et = pytz.timezone(TIMEZONE)
month = datetime.now(et).month
all_events = {
1: [],
2: [{“name”: “Home and Garden Show”, “date”: “Feb 6-8”, “venue”: “York Expo Center”, “impact”: “HIGH”}],
3: [{“name”: “Lawilowan American Indian Festival”, “date”: “Mar 7-8”, “venue”: “York County”, “impact”: “MODERATE”},
{“name”: “York Saint Patricks Day Parade”, “date”: “Mar 14”, “venue”: “Downtown York”, “impact”: “MODERATE”}],
4: [{“name”: “York Train Show”, “date”: “Apr 20-25”, “venue”: “York Expo Center”, “impact”: “HIGH”}],
5: [{“name”: “Give Local York”, “date”: “Apr 30 - May 1”, “venue”: “York County”, “impact”: “HIGH”},
{“name”: “York Revolution Baseball Opener”, “date”: “May 2026”, “venue”: “WellSpan Park”, “impact”: “MODERATE”}],
6: [{“name”: “York County Pride”, “date”: “Jun 13”, “venue”: “York”, “impact”: “MODERATE”},
{“name”: “Makers Spirit Event”, “date”: “Jun 19-20”, “venue”: “York”, “impact”: “MODERATE”},
{“name”: “Penn-Mar Irish Festival”, “date”: “Jun 20”, “venue”: “York County”, “impact”: “MODERATE”},
{“name”: “Lincoln Highway Conference”, “date”: “Jun 22-26”, “venue”: “York”, “impact”: “HIGH”}],
7: [{“name”: “Mason-Dixon Fair”, “date”: “Jul 6-11”, “venue”: “York Fairgrounds”, “impact”: “HIGH”},
{“name”: “York State Fair”, “date”: “Jul 24 - Aug 2”, “venue”: “York Expo Center”, “impact”: “HIGH”},
{“name”: “Smoke on the Rail BBQ Festival”, “date”: “Jul 24-26”, “venue”: “York”, “impact”: “HIGH”}],
8: [{“name”: “York State Fair continues”, “date”: “Through Aug 2”, “venue”: “York Expo Center”, “impact”: “HIGH”},
{“name”: “Pennsylvania Renaissance Faire”, “date”: “Aug 15 onwards”, “venue”: “Mount Hope Estate”, “impact”: “MODERATE”}],
9: [{“name”: “Wild and Uncommon Weekend”, “date”: “Sep 17-20”, “venue”: “Horn Farm Center”, “impact”: “MODERATE”},
{“name”: “Enchanted Fairy Festival”, “date”: “Sep 19”, “venue”: “York County”, “impact”: “MODERATE”},
{“name”: “Fall Native Plant Sale”, “date”: “Sep 12”, “venue”: “York County Parks”, “impact”: “LOW”}],
10: [{“name”: “Pennsylvania Renaissance Faire”, “date”: “Through Oct 25”, “venue”: “Mount Hope Estate”, “impact”: “MODERATE”}],
11: [],
12: [{“name”: “Christmas Magic Festival of Lights”, “date”: “Dec seasonal”, “venue”: “York County”, “impact”: “MODERATE”}],
}
return all_events.get(month, [])

def get_dates():
et = pytz.timezone(TIMEZONE)
today = datetime.now(et).date()
days_until_friday = (4 - today.weekday()) % 7
if days_until_friday == 0:
days_until_friday = 7
next_friday = today + timedelta(days=days_until_friday)
next_saturday = next_friday + timedelta(days=1)
return str(today), str(next_friday), str(next_saturday)

def fetch_rate(hotel_id, checkin):
checkout = str(datetime.strptime(checkin, “%Y-%m-%d”).date() + timedelta(days=1))
url = “https://booking-com.p.rapidapi.com/v1/hotels/room-list”
headers = {
“X-RapidAPI-Key”: RAPIDAPI_KEY,
“X-RapidAPI-Host”: “booking-com.p.rapidapi.com”
}
params = {
“hotel_id”: hotel_id,
“checkin_date”: checkin,
“checkout_date”: checkout,
“adults_number”: “1”,
“room_number”: “1”,
“units”: “metric”,
“currency”: “USD”,
“locale”: “en-us”,
}
try:
response = requests.get(url, headers=headers, params=params, timeout=15)
data = response.json()
lowest = None
rooms = data.get(“rooms”, {})
for room_id, room_data in rooms.items():
for block in room_data.get(“block”, []):
price = block.get(“price_breakdown”, {}).get(“gross_price”)
if price is not None:
if lowest is None or price < lowest:
lowest = price
if lowest is not None:
return “$” + str(int(round(lowest)))
else:
return “N/A”
except Exception as e:
print(“Error fetching hotel “ + hotel_id + “ for “ + checkin + “: “ + str(e))
return “N/A”

def rate_color(rate_str):
if rate_str == “N/A”:
return “#888888”
try:
val = int(rate_str.replace(”$”, “”))
if val >= 100:
return “#c0392b”
if val >= 75:
return “#e07800”
return “#2a7a2a”
except Exception:
return “#888888”

def fmt_date(d):
dt = datetime.strptime(d, “%Y-%m-%d”)
return dt.strftime(”%A, %B “) + str(dt.day) + “, “ + str(dt.year)

def get_lowest(hotel_rates, date_str):
vals = []
for hotel in HOTELS:
r = hotel_rates.get(hotel[“name”], {}).get(date_str, “N/A”)
if r != “N/A”:
try:
vals.append(int(r.replace(”$”, “”)))
except Exception:
pass
if vals:
return “$” + str(min(vals))
return “N/A”

def get_highest(hotel_rates, date_str):
vals = []
for hotel in HOTELS:
r = hotel_rates.get(hotel[“name”], {}).get(date_str, “N/A”)
if r != “N/A”:
try:
vals.append(int(r.replace(”$”, “”)))
except Exception:
pass
if vals:
return “$” + str(max(vals))
return “N/A”

def build_email(hotel_rates, dates, events):
today_str, friday_str, saturday_str = dates
et = pytz.timezone(TIMEZONE)
now = datetime.now(et)
send_time = now.strftime(”%B “) + str(now.day) + “, “ + str(now.year) + “ at 7:00 AM ET”

```
today_rows = ""
for i, hotel in enumerate(HOTELS):
    rate = hotel_rates.get(hotel["name"], {}).get(today_str, "N/A")
    color = rate_color(rate)
    today_rows += "<tr>"
    today_rows += "<td style='padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;color:#555;width:24px;'>" + str(i + 1) + ".</td>"
    today_rows += "<td style='padding:12px 8px;border-bottom:1px solid #f0ece3;font-size:13px;font-weight:600;color:#1a1a1a;'>" + hotel["display"] + "</td>"
    today_rows += "<td style='padding:12px 8px;border-bottom:1px solid #f0ece3;text-align:right;font-size:20px;font-weight:700;color:" + color + ";'>" + rate + "</td>"
    today_rows += "</tr>"

friday_rows = ""
for hotel in HOTELS:
    rate = hotel_rates.get(hotel["name"], {}).get(friday_str, "N/A")
    color = rate_color(rate)
    friday_rows += "<tr>"
    friday_rows += "<td style='padding:9px 8px;border-bottom:1px solid #f5f2ec;font-size:12px;color:#444;'>" + hotel["display"] + "</td>"
    friday_rows += "<td style='padding:9px 8px;border-bottom:1px solid #f5f2ec;text-align:right;font-size:14px;font-weight:700;color:" + color + ";'>" + rate + "</td>"
    friday_rows += "</tr>"

saturday_rows = ""
for hotel in HOTELS:
    rate = hotel_rates.get(hotel["name"], {}).get(saturday_str, "N/A")
    color = rate_color(rate)
    saturday_rows += "<tr>"
    saturday_rows += "<td style='padding:9px 8px;border-bottom:1px solid #f5f2ec;font-size:12px;color:#444;'>" + hotel["display"] + "</td>"
    saturday_rows += "<td style='padding:9px 8px;border-bottom:1px solid #f5f2ec;text-align:right;font-size:14px;font-weight:700;color:" + color + ";'>" + rate + "</td>"
    saturday_rows += "</tr>"

event_rows = ""
if events:
    for ev in events:
        imp = ev.get("impact", "LOW")
        if imp == "HIGH":
            imp_color = "#c0392b"
        elif imp == "MODERATE":
            imp_color = "#e07800"
        else:
            imp_color = "#2a7a2a"
        event_rows += "<tr>"
        event_rows += "<td style='padding:11px 8px;border-bottom:1px solid #f0ece3;'>"
        event_rows += "<span style='font-size:13px;font-weight:600;color:#1b2e1b;'>" + ev["name"] + "</span><br>"
        event_rows += "<span style='font-size:11px;color:#999;'>" + ev["date"] + " - " + ev["venue"] + "</span>"
        event_rows += "</td>"
        event_rows += "<td style='padding:11px 8px;border-bottom:1px solid #f0ece3;text-align:right;'>"
        event_rows += "<span style='background:" + imp_color + ";color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;'>" + imp + "</span>"
        event_rows += "</td>"
        event_rows += "</tr>"
else:
    event_rows = "<tr><td colspan='2' style='padding:14px 8px;color:#888;font-size:13px;'>No major events this month.</td></tr>"

lowest_tonight = get_lowest(hotel_rates, today_str)
highest_tonight = get_highest(hotel_rates, today_str)

html = "<!DOCTYPE html><html><head><meta charset='UTF-8'></head>"
html += "<body style='margin:0;padding:20px;background:#edeae3;font-family:Arial,sans-serif;'>"
html += "<div style='max-width:640px;margin:0 auto;background:#ffffff;border-radius:3px;overflow:hidden;box-shadow:0 4px 30px rgba(0,0,0,0.12);'>"

html += "<div style='background:#1b2e1b;padding:32px 36px;'>"
html += "<div style='font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#7eab6e;margin-bottom:8px;font-weight:600;'>York, Pennsylvania - Daily Rate Report</div>"
html += "<div style='font-size:26px;font-weight:700;color:#ffffff;margin-bottom:4px;'>Hotel Rate Alert</div>"
html += "<div style='font-size:12px;color:#9ab890;margin-bottom:16px;'>Your 7:00 AM briefing - " + send_time + "</div>"
html += "<span style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;'>Today + Weekend</span>"
html += "<span style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;margin-right:6px;'>7 Properties</span>"
html += "<span style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:11px;color:#c0d4b8;'>Live from Booking.com</span>"
html += "</div>"

html += "<table width='100%' cellpadding='0' cellspacing='0' style='background:#1b2e1b;border-top:1px solid rgba(255,255,255,0.08);'><tr>"
html += "<td width='33%' style='padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);'>"
html += "<div style='font-size:22px;font-weight:700;color:#ffffff;'>" + lowest_tonight + "</div>"
html += "<div style='font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;'>Lowest Tonight</div></td>"
html += "<td width='33%' style='padding:14px 10px;text-align:center;border-right:1px solid rgba(255,255,255,0.07);'>"
html += "<div style='font-size:22px;font-weight:700;color:#ffffff;'>" + highest_tonight + "</div>"
html += "<div style='font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;'>Highest Tonight</div></td>"
html += "<td width='33%' style='padding:14px 10px;text-align:center;'>"
html += "<div style='font-size:22px;font-weight:700;color:#ffffff;'>7 Hotels</div>"
html += "<div style='font-size:9px;color:#5e8a5e;letter-spacing:1px;text-transform:uppercase;'>Tracked Tonight</div></td>"
html += "</tr></table>"

html += "<div style='padding:24px 36px 0;'>"
html += "<div style='font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;'>Todays Rates - " + fmt_date(today_str) + "</div>"
html += "</div>"
html += "<table width='100%' cellpadding='0' cellspacing='0' style='padding:0 36px;'><tbody>" + today_rows + "</tbody></table>"

html += "<div style='padding:24px 36px 0;margin-top:10px;'>"
html += "<div style='font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:14px;'>Following Weekend Rates</div>"
html += "<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom:16px;border:1px solid #ebe7e0;border-radius:6px;overflow:hidden;'>"
html += "<thead><tr style='background:#f7f4ef;'><th colspan='2' style='padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#555;'>Friday - " + fmt_date(friday_str) + "</th></tr></thead>"
html += "<tbody>" + friday_rows + "</tbody></table>"
html += "<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom:24px;border:1px solid #ebe7e0;border-radius:6px;overflow:hidden;'>"
html += "<thead><tr style='background:#f7f4ef;'><th colspan='2' style='padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#555;'>Saturday - " + fmt_date(saturday_str) + "</th></tr></thead>"
html += "<tbody>" + saturday_rows + "</tbody></table>"
html += "</div>"

html += "<div style='padding:0 36px;'>"
html += "<div style='font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#999;font-weight:700;padding-bottom:10px;border-bottom:2px solid #f0ece3;margin-bottom:4px;'>York PA Events - Rate Impact Watch</div>"
html += "<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom:24px;'><tbody>" + event_rows + "</tbody></table>"
html += "</div>"

html += "<div style='padding:12px 36px;background:#f7f4ef;border-top:1px solid #ebe7e0;'>"
html += "<span style='font-size:11px;color:#888;'>Rate Legend: "
html += "<span style='color:#2a7a2a;font-weight:700;'>Under $75 - Soft</span> | "
html += "<span style='color:#e07800;font-weight:700;'>$75-$99 - Moderate</span> | "
html += "<span style='color:#c0392b;font-weight:700;'>$100 and above - High</span></span>"
html += "</div>"

html += "<div style='background:#1b2e1b;padding:18px 36px;text-align:center;'>"
html += "<p style='font-size:11px;color:#5e8a5e;margin:0;line-height:1.8;'>"
html += "York PA Hotel Rate Alert - Sent daily at 7:00 AM ET<br>"
html += "Ramada | Inn at York | Motel 6 x2 | Red Roof | Days Inn | Quality Inn East<br>"
html += "Rates sourced live from Booking.com via RapidAPI<br>"
html += "Delivered to: khushbudave24@gmail.com"
html += "</p></div>"

html += "</div></body></html>"
return html
```

def send_email(html_content, dates):
today_str = dates[0]
dt = datetime.strptime(today_str, “%Y-%m-%d”)
subject = “York PA Hotel Rates - “ + dt.strftime(”%B “) + str(dt.day) + “, “ + str(dt.year)
msg = MIMEMultipart(“alternative”)
msg[“Subject”] = subject
msg[“From”] = SENDER_EMAIL
msg[“To”] = RECIPIENT_EMAIL
msg.attach(MIMEText(html_content, “html”))
try:
with smtplib.SMTP_SSL(“smtp.gmail.com”, 465) as server:
server.login(SENDER_EMAIL, SENDER_PASSWORD)
server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
print(“Email sent successfully to “ + RECIPIENT_EMAIL)
except Exception as e:
print(“Email failed: “ + str(e))
raise

def main():
print(“York PA Hotel Rate Monitor starting…”)
dates = get_dates()
today_str, friday_str, saturday_str = dates
print(“Fetching rates for: “ + today_str + “, “ + friday_str + “, “ + saturday_str)
hotel_rates = {}
for hotel in HOTELS:
print(“Fetching: “ + hotel[“display”])
hotel_rates[hotel[“name”]] = {}
for date in [today_str, friday_str, saturday_str]:
rate = fetch_rate(hotel[“booking_id”], date)
hotel_rates[hotel[“name”]][date] = rate
print(”  “ + date + “: “ + rate)
time.sleep(1)
print(“Checking York PA events…”)
events = get_events()
print(“Found “ + str(len(events)) + “ events this month”)
print(“Building and sending email…”)
html = build_email(hotel_rates, dates, events)
send_email(html, dates)
print(“Done!”)

if **name** == “**main**”:
main()
