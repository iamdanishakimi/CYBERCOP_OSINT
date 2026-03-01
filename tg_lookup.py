import asyncio
from telethon.sync import TelegramClient
from telethon.tl import types, functions

# --- Config ---
api_id = 32076729
api_hash = "9c6cebfae536b8c97e12cb90b0537187"
session_name = "cybercop_session"

# --- ANSI Colors ---
C = "\033[96m"
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
W = "\033[0m"
B = "\033[1m"

def get_human_readable_user_status(status):
    from telethon.tl import types
    if isinstance(status, types.UserStatusOnline): return "Currently online"
    elif isinstance(status, types.UserStatusOffline): return status.was_online.strftime("%Y-%m-%d %H:%M:%S") if getattr(status, 'was_online', None) else "Offline"
    elif isinstance(status, types.UserStatusRecently): return "Last seen recently"
    elif isinstance(status, types.UserStatusLastWeek): return "Last seen last week"
    elif isinstance(status, types.UserStatusLastMonth): return "Last seen last month"
    return "Unknown"

async def lookup_by_id(user_input):
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"{R}[!] Not logged in. Run telegram_login.py first.{W}")
        await client.disconnect()
        return

    try:
        # Try to resolve the input (works for @username or numeric ID)
        try:
            user_id = int(user_input)
        except ValueError:
            user_id = user_input  # treat as @username

        entity = await client.get_entity(user_id)

        if not isinstance(entity, types.User):
            print(f"{R}[!] This ID belongs to a group/channel, not a user.{W}")
            await client.disconnect()
            return

        print(f"\n{B}{C}{'='*50}{W}")
        print(f"       TELEGRAM USER LOOKUP")
        print(f"{B}{C}{'='*50}{W}")

        sp = "\n "
        print(f" {B}[+]{W} ID         : {entity.id}")
        print(f" {B}[+]{W} First Name : {entity.first_name or 'N/A'}")
        print(f" {B}[+]{W} Last Name  : {entity.last_name or 'N/A'}")
        print(f" {B}[+]{W} Username   : @{entity.username}" if entity.username else f" {B}[+]{W} Username   : None")
        print(f" {B}[+]{W} Phone      : {C}{entity.phone or 'Hidden / Not Shared'}{W}")
        print(f" {B}[+]{W} Status     : {get_human_readable_user_status(entity.status)}")
        print(f" {B}[+]{W} Verified   : {entity.verified}")
        print(f" {B}[+]{W} Bot        : {entity.bot}")
        print(f"{B}{C}{'='*50}{W}\n")

    except ValueError as e:
        print(f"{R}[!] Could not find user: {e}{W}")
    except Exception as e:
        print(f"{R}[!] Error: {e}{W}")

    await client.disconnect()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"{Y}Usage: python tg_lookup.py <user_id or @username>{W}")
        print(f"{Y}Example: python tg_lookup.py 123456789{W}")
        print(f"{Y}Example: python tg_lookup.py @someusername{W}")
        sys.exit(1)

    target = sys.argv[1]
    asyncio.run(lookup_by_id(target))