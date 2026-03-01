import requests
import sys
import threading
import json
import re
import hashlib
import phonenumbers
import asyncio
from getpass import getpass
from telethon.sync import TelegramClient, functions
from telethon.tl import types
from phonenumbers import geocoder, carrier
from playwright.sync_api import sync_playwright
import dns.resolver
import whois

# --- ANSI Colors for Beautification ---
C = "\033[96m"  # Cyan
G = "\033[92m"  # Green
R = "\033[91m"  # Red
Y = "\033[93m"  # Yellow
W = "\033[0m"   # White / Reset
B = "\033[1m"   # Bold

if len(sys.argv) != 2:
    print(f"{R}[!] Usage: python3 CYBERCOP_OSINT.py <phone_number | email>{W}")
    sys.exit(1)

target = sys.argv[1]
mode = "email" if "@" in target else "phone"
results = []

# Keep backward compat for phone modules
if mode == "phone":
    number = target

def get_headers(referer=""):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive",
        "Referer": referer
    }

# --- 1. Flipkart Module ---
def check_flipkart(number, result):
    try:
        num = f"+60{number}"
        url = "https://2.rome.api.flipkart.com/api/6/user/signup/status"
        
        headers = get_headers("https://www.flipkart.com/")
        headers.update({
            "Content-Type": "application/json",
            "X-User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0 FKUA/website/42/website/Desktop",
            "Origin": "https://www.flipkart.com"
        })
        payload = {"loginId": [num], "supportAllStates": True}
        
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if res.status_code == 200:
            status = res.json().get("RESPONSE", {}).get("userDetails", {}).get(num, "")
            if status == "VERIFIED":
                result.append({"Flipkart": f"{G}Registered (True){W}"})
            elif status == "NOT_FOUND":
                result.append({"Flipkart": f"{R}Not Registered (False){W}"})
            else:
                result.append({"Flipkart": f"{Y}Unknown Response{W}"})
        else:
            result.append({"Flipkart": f"{R}Blocked (Status: {res.status_code}){W}"})
    except Exception as e:
        result.append({"Flipkart": f"{R}Error: {str(e)}{W}"})

# --- 2. Swiggy Module ---
def check_swiggy(number, result):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent=get_headers()["User-Agent"])
            page = context.new_page()
            page.goto("https://www.swiggy.com", wait_until="networkidle")

            js_code = f"""
            async () => {{
                let res = await fetch('https://www.swiggy.com/dapi/auth/signin-with-check', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', '__fetch_req__': 'true', 'Platform': 'dweb' }},
                    body: JSON.stringify({{ mobile: '{number}', password: '', _csrf: window._csrfToken }})
                }});
                return await res.json();
            }}
            """
            response_json = page.evaluate(js_code)
            is_registered = response_json.get("data", {}).get("registered")
            
            if is_registered is True:
                result.append({"Swiggy": f"{G}Registered (True){W}"})
            elif is_registered is False:
                result.append({"Swiggy": f"{R}Not Registered (False){W}"})
            else:
                result.append({"Swiggy": f"{Y}Unknown Response{W}"})
            browser.close()
    except Exception as e:
        result.append({"Swiggy": f"{R}Error: {str(e)}{W}"})

# --- 3. Twitter Module ---
def check_twitter(number, result):
    try:
        base_url = "https://twitter.com/account/begin_password_reset"
        session = requests.Session()
        headers = get_headers("https://twitter.com/")
        res = session.get(base_url, headers=headers, timeout=10)
        
        auth_match = re.search(r'<input type="hidden" name="authenticity_token" value="([^"]*)">', res.text)
        if not auth_match:
            result.append({"Twitter": f"{R}Blocked (No CSRF Token){W}"})
            return
            
        data = {"authenticity_token": auth_match.group(1), "account_identifier": number}
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        res = session.post(base_url, data=data, headers=headers, allow_redirects=False, timeout=10)
        if res.status_code == 302 and "send_password_reset" in str(res.headers.get("location")):
            result.append({"Twitter": f"{G}Registered (True){W}"})
        else:
            result.append({"Twitter": f"{R}Not Registered (False){W}"})
    except Exception as e:
        result.append({"Twitter": f"{R}Error: {str(e)}{W}"})

# --- 4. Cellular Intelligence ---
def check_cellular(number, result):
    try:
        parsed_number = phonenumbers.parse(f"+60{number}")
        if phonenumbers.is_valid_number(parsed_number):
            circle = geocoder.description_for_number(parsed_number, "en") or "India"
            operator_name = carrier.name_for_number(parsed_number, "en") or "Unknown Operator"
            result.append({"Cellular Data": f"{C}{operator_name} - {circle}{W}"})
        else:
            result.append({"Cellular Data": f"{R}Invalid Number{W}"})
    except Exception as e:
        result.append({"Cellular Data": f"{R}Error: {str(e)}{W}"})

# --- 5. Instagram Module ---
def check_instagram(number, result):
    try:
        session = requests.Session()
        headers = get_headers("https://www.instagram.com/")
        res = session.get("https://www.instagram.com/accounts/login/", headers=headers, timeout=10)

        csrf_token = res.cookies.get("csrftoken", "")
        if not csrf_token:
            match = re.search(r'"csrf_token":"([^"]*)"', res.text)
            if match:
                csrf_token = match.group(1)

        if not csrf_token:
            result.append({"Instagram": f"{R}Blocked (No CSRF Token){W}"})
            return

        headers.update({
            "X-CSRFToken": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.instagram.com",
            "Referer": "https://www.instagram.com/accounts/login/"
        })

        phone = f"+60{number}"
        data = {"q": phone, "skip_recovery": "1"}

        res = session.post("https://www.instagram.com/api/v1/users/lookup/",
                          headers=headers, data=data, timeout=10)

        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("user"):
                result.append({"Instagram": f"{G}Registered (True){W}"})
            else:
                result.append({"Instagram": f"{R}Not Registered (False){W}"})
        elif res.status_code == 404:
            result.append({"Instagram": f"{R}Not Registered (False){W}"})
        else:
            result.append({"Instagram": f"{R}Blocked (Status: {res.status_code}){W}"})
    except Exception as e:
        result.append({"Instagram": f"{R}Error: {str(e)}{W}"})

# --- 6. Telegram OSINT Module ---
def get_human_readable_user_status(status):
    if isinstance(status, types.UserStatusOnline): return "Currently online"
    elif isinstance(status, types.UserStatusOffline): return status.was_online.strftime("%Y-%m-%d %H:%M:%S") if getattr(status, 'was_online', None) else "Offline"
    elif isinstance(status, types.UserStatusRecently): return "Last seen recently"
    elif isinstance(status, types.UserStatusLastWeek): return "Last seen last week"
    elif isinstance(status, types.UserStatusLastMonth): return "Last seen last month"
    return "Unknown"

async def _telegram_logic(number):
    api_id = 32076729
    api_hash = "9c6cebfae536b8c97e12cb90b0537187"
    session_name = "cybercop_session" 
    client = TelegramClient(session_name, api_id, api_hash)
    
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return f"{R}Auth Required! Need to login first.{W}"

    try:
        contact = types.InputPhoneContact(client_id=0, phone=f"+60{number}", first_name="", last_name="")
        contacts = await client(functions.contacts.ImportContactsRequest([contact]))
        
        users = contacts.users

        if len(users) == 0:
            res = f"{R}Not Registered or Private{W}"
        else:
            raw_user = users[0]
            
            await client(functions.contacts.DeleteContactsRequest(id=[raw_user.id])) 
            
            u_id = raw_user.id
            u_user = f"@{raw_user.username}" if raw_user.username else "None"
            
            f_name = raw_user.first_name or ""
            l_name = raw_user.last_name or ""
            name = f"{f_name} {l_name}".strip() if (f_name or l_name) else "Unknown"
            
            phone = raw_user.phone or "Hidden/None"
            status = get_human_readable_user_status(raw_user.status)
            verified = raw_user.verified
            bot = raw_user.bot
            
            sp = "\n" + (" " * 22) 
            res = f"{G}Found!{W}"
            res += f"{sp}{C}├─ ID{W}       : {u_id}"
            res += f"{sp}{C}├─ Name{W}     : {name}"
            res += f"{sp}{C}├─ Username{W} : {u_user}"
            res += f"{sp}{C}├─ Phone{W}    : {phone}"
            res += f"{sp}{C}├─ Status{W}   : {status}"
            res += f"{sp}{C}├─ Verified{W} : {verified}"
            res += f"{sp}{C}└─ Bot{W}      : {bot}"
            
    except Exception as e:
        res = f"{R}Error: {str(e)}{W}"
    
    await client.disconnect() 
    return res

def check_telegram(number, result):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tg_result = loop.run_until_complete(_telegram_logic(number))
        result.append({"Telegram": tg_result})
        loop.close()
    except Exception as e:
        result.append({"Telegram": f"{R}Error: {str(e)}{W}"})

# ============================================
#        EMAIL OSINT MODULES
# ============================================

# --- E1. Email Validation Module ---
def check_email_validation(email, result):
    try:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            result.append({"Validation": f"{R}Invalid Email Format{W}"})
            return

        domain = email.split("@")[1]
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange).rstrip('.')
            result.append({"Validation": f"{G}Valid Format | MX: {mx_host}{W}"})
        except dns.resolver.NoAnswer:
            result.append({"Validation": f"{Y}Valid Format | No MX Record{W}"})
        except dns.resolver.NXDOMAIN:
            result.append({"Validation": f"{R}Valid Format | Domain Does Not Exist{W}"})
        except Exception:
            result.append({"Validation": f"{Y}Valid Format | MX Lookup Failed{W}"})
    except Exception as e:
        result.append({"Validation": f"{R}Error: {str(e)}{W}"})

# --- E2. EmailRep.io Module (Reputation + Breaches) ---
def check_emailrep(email, result):
    try:
        url = f"https://emailrep.io/{email}"
        headers = get_headers()
        headers["Accept"] = "application/json"
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code == 200:
            data = res.json()
            reputation = data.get("reputation", "unknown")
            suspicious = data.get("suspicious", False)
            references = data.get("references", 0)
            details = data.get("details", {})
            breach_count = details.get("data_breach", False)
            profiles = details.get("profiles", [])

            rep_color = G if reputation == "high" else Y if reputation == "medium" else R
            result.append({"Reputation": f"{rep_color}{reputation.upper()}{W} | Suspicious: {suspicious} | References: {references}"})

            if breach_count:
                result.append({"Breaches": f"{R}Exposed in data breaches{W}"})
            else:
                result.append({"Breaches": f"{G}No known breaches{W}"})

            if profiles:
                profile_str = ", ".join(profiles)
                result.append({"Profiles": f"{G}{profile_str}{W}"})
            else:
                result.append({"Profiles": f"{Y}No profiles found{W}"})
        elif res.status_code == 429:
            result.append({"Reputation": f"{Y}Rate Limited (try again later){W}"})
            result.append({"Breaches": f"{Y}Rate Limited{W}"})
            result.append({"Profiles": f"{Y}Rate Limited{W}"})
        else:
            result.append({"Reputation": f"{R}API Error (Status: {res.status_code}){W}"})
            result.append({"Breaches": f"{R}API Error{W}"})
            result.append({"Profiles": f"{R}API Error{W}"})
    except Exception as e:
        result.append({"Reputation": f"{R}Error: {str(e)}{W}"})
        result.append({"Breaches": f"{R}Error{W}"})
        result.append({"Profiles": f"{R}Error{W}"})

# --- E3. Domain Info Module (WHOIS + MX) ---
def check_domain_info(email, result):
    try:
        domain = email.split("@")[1]
        try:
            w = whois.whois(domain)
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]
            registrar = w.registrar or "Unknown"
            org = w.org or "N/A"
            creation_str = creation.strftime("%Y-%m-%d") if creation else "Unknown"
            result.append({"Domain Info": f"{C}Created: {creation_str} | Registrar: {registrar} | Org: {org}{W}"})
        except Exception:
            result.append({"Domain Info": f"{Y}WHOIS lookup failed for {domain}{W}"})
    except Exception as e:
        result.append({"Domain Info": f"{R}Error: {str(e)}{W}"})

# --- E4. Gravatar Module ---
def check_gravatar(email, result):
    try:
        email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
        url = f"https://gravatar.com/{email_hash}.json"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            entry = data.get("entry", [{}])[0]
            display_name = entry.get("displayName", "N/A")
            profile_url = entry.get("profileUrl", "N/A")
            result.append({"Gravatar": f"{G}Found! | Name: {display_name} | {profile_url}{W}"})
        elif res.status_code == 404:
            result.append({"Gravatar": f"{R}No profile found{W}"})
        else:
            result.append({"Gravatar": f"{Y}Unexpected response (Status: {res.status_code}){W}"})
    except Exception as e:
        result.append({"Gravatar": f"{R}Error: {str(e)}{W}"})

# --- E5. GitHub Module ---
def check_github(email, result):
    try:
        url = f"https://api.github.com/search/users?q={email}+in:email"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "CYBERCOP-OSINT"}
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code == 200:
            data = res.json()
            count = data.get("total_count", 0)
            if count > 0:
                user = data["items"][0]
                login = user.get("login", "N/A")
                html_url = user.get("html_url", "")
                result.append({"GitHub": f"{G}Found! | @{login} | {html_url}{W}"})
            else:
                result.append({"GitHub": f"{R}No account found{W}"})
        elif res.status_code == 403:
            result.append({"GitHub": f"{Y}Rate Limited (60 req/hr){W}"})
        else:
            result.append({"GitHub": f"{R}API Error (Status: {res.status_code}){W}"})
    except Exception as e:
        result.append({"GitHub": f"{R}Error: {str(e)}{W}"})

# --- E6. Disposable Email Check ---
def check_disposable(email, result):
    try:
        url = f"https://disposable.debounce.io/?email={email}"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            is_disposable = data.get("disposable", "false")
            if is_disposable == "true":
                result.append({"Disposable": f"{R}Yes - Temporary/Disposable Email{W}"})
            else:
                result.append({"Disposable": f"{G}No - Legitimate Email Provider{W}"})
        else:
            result.append({"Disposable": f"{Y}Check failed (Status: {res.status_code}){W}"})
    except Exception as e:
        result.append({"Disposable": f"{R}Error: {str(e)}{W}"})

# --- Main Execution ---
if __name__ == "__main__":
    print(f"\n{B}{C}[*] CYBERCOP OSINT INITIALIZED [*]{W}")

    threads = []

    if mode == "phone":
        print(f"{Y}[~] Scanning targets for : +60 {number}{W}\n")

        threads.append(threading.Thread(target=check_flipkart, args=(number, results)))
        threads.append(threading.Thread(target=check_swiggy, args=(number, results)))
        threads.append(threading.Thread(target=check_twitter, args=(number, results)))
        threads.append(threading.Thread(target=check_cellular, args=(number, results)))
        threads.append(threading.Thread(target=check_instagram, args=(number, results)))
        threads.append(threading.Thread(target=check_telegram, args=(number, results)))

        report_title = f"+60 {number}"
    else:
        print(f"{Y}[~] Scanning email target : {target}{W}\n")

        threads.append(threading.Thread(target=check_email_validation, args=(target, results)))
        threads.append(threading.Thread(target=check_emailrep, args=(target, results)))
        threads.append(threading.Thread(target=check_domain_info, args=(target, results)))
        threads.append(threading.Thread(target=check_gravatar, args=(target, results)))
        threads.append(threading.Thread(target=check_github, args=(target, results)))
        threads.append(threading.Thread(target=check_disposable, args=(target, results)))

        report_title = target

    for thread in threads:
        thread.daemon = True
        thread.start()

    for thread in threads:
        thread.join()

    print(f"{B}{C}" + "="*55)
    print(f"       OSINT REPORT FOR: {report_title}")
    print("="*55 + f"{W}")

    # Preserve display order
    if mode == "phone":
        order = ["Flipkart", "Swiggy", "Twitter", "Cellular Data", "Instagram", "Telegram"]
    else:
        order = ["Validation", "Reputation", "Breaches", "Disposable", "Domain Info", "Gravatar", "GitHub", "Profiles"]

    final_dict = {}
    for r in results:
        final_dict.update(r)

    for key in order:
        if key in final_dict:
            print(f" {B}[+]{W} {key:<15}: {final_dict[key]}")

    print(f"{B}{C}" + "="*55 + f"{W}\n")
