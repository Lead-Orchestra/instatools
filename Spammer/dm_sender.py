# -*- coding: utf-8 -*-
"""
Instagram DM Sender with Anti-Bot Detection
============================================

This script sends Instagram DMs with advanced anti-detection features:
- Session persistence (reuses existing sessions)
- Human-like delays between messages
- Device fingerprint simulation
- Optional proxy support
- Rate limiting to avoid detection

Usage:
    # Using session file (recommended - no bot detection):
    uv run python dm_sender.py --session ../alissa.montez.session --targets targets.txt --message "Hey! How are you?"
    
    # Using username/password (more risky):
    uv run python dm_sender.py -u username -p password --targets targets.txt --message "Hey!"
    
    # Non-interactive mode for automation:
    uv run python dm_sender.py --session ../alissa.montez.session --targets targets.txt --message "Hello!" --non-interactive
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

from instagrapi import Client
from instagrapi.types import DirectThread
from instagrapi.exceptions import ChallengeRequired, ClientLoginRequired, LoginRequired

# Anti-detection device settings - simulates a real phone
# Version updated to match a current Instagram Android build (Feb 4, 2026).
DEVICE_SETTINGS = {
    "app_version": "415.0.0.36.76",
    "android_version": "28",  # Android 9.0 Pie
    "android_release": "9",
    "dpi": "480dpi",
    "resolution": "1080x1920",
    "manufacturer": "samsung",
    "device": "dreamlte",
    "model": "SM-G950F",
    "cpu": "samsungexynos8895",
    "version_code": "382105877",
}

# User agent to match device
USER_AGENT = (
    "Instagram 415.0.0.36.76 Android (28/9; 480dpi; 1080x1920; "
    "samsung; SM-G950F; dreamlte; samsungexynos8895; en_US; 382105877)"
)

def load_env_credentials():
    """Manually parse .env file for IG credentials to avoid extra dependencies."""
    creds = {"username": None, "password": None}
    try:
        # Search for .env in parent directories (up to 4 levels)
        current_dir = Path(__file__).parent.absolute()
        check_path = current_dir
        for _ in range(5):
            env_path = check_path / ".env"
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, val = line.split("=", 1)
                            val = val.strip("'").strip('"')
                            if key == "IGIFI_USERNAME":
                                creds["username"] = val
                            elif key == "IGFI_PASSWORD":
                                creds["password"] = val
                if creds["username"]:
                    print(f"[*] Found credentials in {env_path}")
                    return creds
            if check_path == check_path.parent:
                break
            check_path = check_path.parent
    except Exception as e:
        print(f"[*] Note: Could not auto-load .env: {e}")
    return creds


def random_delay(min_sec: float = 3.0, max_sec: float = 8.0):
    """Add human-like random delay between actions."""
    delay = random.uniform(min_sec, max_sec)
    print(f"[*] Waiting {delay:.1f}s...")
    time.sleep(delay)


def challenge_code_handler(username, choice):
    """Prompt for an Instagram checkpoint/challenge code."""
    print(f"[!] Verification required for @{username} via {choice}")
    
    # Check if we are in non-interactive mode (this is a bit of a hack since args isn't global)
    # But we can check sys.argv
    if '--non-interactive' in sys.argv:
        print(f"[✘] Cannot provide code in non-interactive mode. Please run without --non-interactive.")
        raise Exception("Mobile checkpoint required (non-interactive mode)")
        
    code = input(f"[?] Please enter the code sent to your {choice}: ").strip()
    return code


def resolve_challenge(client: Client, exception: Exception):
    """Attempt to solve a challenge/checkpoint using instagrapi's resolution helpers."""
    import traceback
    try:
        print(f"[*] Security challenge detected: {exception}")

        # Ensure handler is set (sometimes cleared by instagrapi during login failure)
        client.challenge_code_handler = challenge_code_handler
        # Some versions might check change_password_handler
        client.change_password_handler = lambda *args: None

        print(f"[*] Attempting interactive resolution for @{client.username or 'user'}...")

        resolved = False

        # Prefer resolving directly from the exception payload when available.
        if hasattr(client, "challenge_resolve") and hasattr(exception, "response_json"):
            try:
                print("[*] Native challenge detected, launching resolver...")
                client.challenge_resolve(exception.response_json)
                resolved = True
                return True
            except Exception as te:
                print(f"[!] Direct challenge resolution failed ({te}). Trying handle_exception...")
        else:
            try:
                last_json = getattr(client, "last_json", None)
                has_last_json = bool(last_json)
            except Exception:
                last_json = None
                has_last_json = False
            print(f"[*] Challenge payload available: response_json={hasattr(exception, 'response_json')}, last_json={has_last_json}")
            if has_last_json and hasattr(client, "challenge_resolve"):
                try:
                    lj_keys = list(last_json.keys())
                    step_name = last_json.get("step_name")
                    challenge_api_path = last_json.get("challenge", {}).get("api_path") or last_json.get("checkpoint_url")
                    print(f"[*] last_json keys: {lj_keys}")
                    if step_name:
                        print(f"[*] last_json step_name: {step_name}")
                    if challenge_api_path:
                        print(f"[*] last_json challenge path: {challenge_api_path}")

                    if step_name and challenge_api_path and hasattr(client, "challenge_resolve_simple"):
                        print("[*] Using challenge_resolve_simple...")
                        client.challenge_resolve_simple(challenge_api_path)
                    else:
                        print("[*] Using challenge_resolve...")
                        client.challenge_resolve(last_json)
                    resolved = True
                    return True
                except Exception as te:
                    print(f"[!] last_json resolution failed ({te}). Trying handle_exception...")

        # client.handle_exception is the official way to handle challenges
        try:
            if hasattr(client, "handle_exception") and callable(client.handle_exception):
                client.handle_exception(exception)
                resolved = True
                return True
        except (TypeError, Exception) as te:
            # If handle_exception failed, try to trigger and resolve a clean challenge flow.
            print(f"[!] Standard resolution failed ({te}). Forcing fresh challenge check...")

            try:
                # This call reliably triggers ChallengeRequired if we are checkpointed
                client.get_timeline_feed()
            except Exception as fresh_e:
                # Resolve using the response payload when available
                if hasattr(client, "challenge_resolve") and hasattr(fresh_e, "response_json"):
                    print("[*] Native challenge detected, launching resolver...")
                    client.challenge_resolve(fresh_e.response_json)
                    return True

            # Fallback: manually call challenge_resolve with last_json if available
            if hasattr(client, "last_json") and client.last_json:
                client.challenge_resolve(client.last_json)
                return True

            raise te

        if not resolved:
            print("[!] No resolver executed. Forcing fresh challenge check...")
            try:
                client.get_timeline_feed()
            except Exception as fresh_e:
                if hasattr(client, "challenge_resolve") and hasattr(fresh_e, "response_json"):
                    print("[*] Native challenge detected, launching resolver...")
                    client.challenge_resolve(fresh_e.response_json)
                    return True

            if hasattr(client, "last_json") and client.last_json:
                client.challenge_resolve(client.last_json)
                return True
            
    except Exception as e:
        err_msg = str(e).lower()
        if "challenge_code_handler" in err_msg:
            print(f"[✘] Challenge resolution error: {e}")
        elif "checkpoint" in err_msg or "challenge" in err_msg:
            print(f"[!] Challenge was not resolved: {e}")
            # print(traceback.format_exc()) # Debugging
        else:
            print(f"[✘] Authentication step failed: {e}")
            print(traceback.format_exc())
    return False


def load_session(client: Client, session_file: str, strip_device_settings: bool = False):
    """Load session from file if it exists. Supports both instaloader and instagrapi formats."""
    if not os.path.exists(session_file):
        print(f"[!] Session file not found: {session_file}")
        return False
    
    # Set challenge handler early
    client.challenge_code_handler = challenge_code_handler
    
    try:
        session_data = None
        
        # Try instaloader pickle format first (created by cookies.py)
        try:
            import pickle
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            if isinstance(session_data, dict) and "sessionid" in session_data:
                print("[*] Detected instaloader session format")

                sessionid = session_data.get("sessionid", "")
                if not sessionid:
                    return False

                # Ensure challenge handler is in place before login
                client.challenge_code_handler = challenge_code_handler

                try:
                    client.login_by_sessionid(sessionid)
                except (ChallengeRequired, ClientLoginRequired, LoginRequired) as e:
                    if resolve_challenge(client, e):
                        return True
                    return "challenge"

                try:
                    user_info = client.account_info()
                    print(f"[✔] Session loaded: @{user_info.username}")
                    return True
                except Exception as e:
                    err_msg = str(e).lower()
                    if "checkpoint" in err_msg or "challenge" in err_msg:
                        if resolve_challenge(client, e):
                            return True
                        return "challenge"
                    return False
                
        except (pickle.UnpicklingError, TypeError, KeyError):
            pass
        
        # Try instagrapi JSON format
        if session_data is None:
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                print(f"[*] Detected instagrapi session format")
                if strip_device_settings and isinstance(session_data, dict):
                    if "device_settings" in session_data or "user_agent" in session_data:
                        session_data.pop("device_settings", None)
                        session_data.pop("user_agent", None)
                        try:
                            with open(session_file, "w") as f:
                                json.dump(session_data, f, indent=2)
                            print("[*] Stripped device settings from session file")
                        except Exception as e:
                            print(f"[!] Failed to update session file: {e}")
                # Try to extract username
                try:
                    username_in_settings = session_data.get('username') or session_data.get('ds_user', '')
                    if username_in_settings:
                        client.username = username_in_settings
                except:
                    pass

                # Prefer login_by_sessionid if present (more reliable than raw set_settings)
                sessionid = (
                    session_data.get("authorization_data", {}).get("sessionid")
                    or session_data.get("sessionid")
                )
                if sessionid:
                    try:
                        client.login_by_sessionid(sessionid)
                        print("[*] login_by_sessionid succeeded")
                    except (ChallengeRequired, ClientLoginRequired, LoginRequired) as e:
                        if resolve_challenge(client, e):
                            return True
                        return "challenge"
                    except Exception as e:
                        print(f"[!] login_by_sessionid failed: {e}")
                        client.set_settings(session_data)
                        auth_data = session_data.get("authorization_data", {})
                        ds_user_id = auth_data.get("ds_user_id")
                        sessionid = auth_data.get("sessionid")
                        if sessionid:
                            client.private.cookies.set("sessionid", sessionid, domain=".instagram.com")
                        if ds_user_id:
                            client.private.cookies.set("ds_user_id", str(ds_user_id), domain=".instagram.com")
                else:
                    client.set_settings(session_data)
            except:
                return False
        
        # Verify and handle challenges
        try:
            # Ensure we have a username set if possible
            if not client.username and isinstance(session_data, dict):
                client.username = session_data.get("username")
                 
            user_info = client.account_info()
            print(f"[✔] Session loaded: @{user_info.username}")
            return True
        except Exception as e:
            err_msg = str(e).lower()
            if "checkpoint" in err_msg or "challenge" in err_msg:
                if resolve_challenge(client, e):
                    try:
                        user_info = client.account_info()
                        print(f"[✔] Challenge solved! @{user_info.username}")
                        return True
                    except:
                        pass
                return "challenge"
            return False
            
    except Exception as e:
        print(f"[!] Error loading session: {e}")
        return False


def login_with_password(client: Client, username: str, password: str, session_file: str = None) -> bool:
    """Login with username/password and save session."""
    try:
        print(f"[*] Logging in as @{username}...")
        random_delay(1, 2)
        
        # Pre-set username so it's available for challenge handlers
        client.username = username
        
        try:
            client.login(username, password)
        except Exception as e:
            err_msg = str(e).lower()
            if "checkpoint" in err_msg or "challenge" in err_msg:
                if not resolve_challenge(client, e):
                    return False
            else:
                raise e
        
        print(f"[✔] Logged in successfully!")
        
        # Save session for future use
        if session_file:
            save_session(client, session_file)
        
        return True
    except Exception as e:
        print(f"[✘] Login failed: {e}")
        return False


def save_session(client: Client, session_file: str):
    """Save session to file for reuse."""
    try:
        with open(session_file, 'w') as f:
            json.dump(client.get_settings(), f, indent=2)
        print(f"[✔] Session saved to: {session_file}")
    except Exception as e:
        print(f"[!] Error saving session: {e}")


def setup_client(proxy: Optional[str] = None, use_default_device: bool = True) -> Client:
    """Create client with anti-detection settings."""
    client = Client()
    
    # Set challenge handler globally
    client.challenge_code_handler = challenge_code_handler

    # Set device settings to look like a real phone unless using defaults
    if not use_default_device:
        client.set_device(DEVICE_SETTINGS)
        client.set_user_agent(USER_AGENT)
    
    # Set proxy if provided
    if proxy:
        client.set_proxy(proxy)
        print(f"[*] Using proxy: {proxy}")
    
    # Set delays to mimic human behavior
    client.delay_range = [2, 5]  # Random delay between requests
    
    return client


def print_challenge_payload(client: Client):
    """Print the last challenge payload if available."""
    try:
        last_json = getattr(client, "last_json", None)
    except Exception:
        last_json = None
    if not last_json:
        print("[!] No challenge payload available.")
        return
    try:
        print("[*] Challenge payload (last_json):")
        print(json.dumps(last_json, indent=2))
    except Exception:
        print("[*] Challenge payload (raw):")
        print(last_json)
    try:
        url = last_json.get("challenge", {}).get("url")
        if url and "unsupported_version" in url:
            print("[!] Instagram returned unsupported_version. Try --use-default-device to use instagrapi defaults.")
    except Exception:
        pass





def load_targets(targets_file: str) -> list[str]:
    """Load target usernames from file."""
    if not os.path.exists(targets_file):
        print(f"[!] Targets file not found: {targets_file}")
        return []
    
    with open(targets_file, 'r') as f:
        targets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"[✔] Loaded {len(targets)} target(s)")
    return targets


def send_dm(client: Client, username: str, message: str, retries: int = 1) -> bool:
    """Send a DM to a single user with anti-detection delays."""
    try:
        # Get user ID from username
        print(f"[*] Looking up @{username}...")
        random_delay(1, 3)
        
        # Use search_users first as it's often more reliable/less strict than user_info
        try:
            search_results = client.search_users(username)
            found = False
            for user in search_results:
                if user.username.lower() == username.lower():
                    user_id = user.pk
                    found = True
                    break
            
            if not found:
                # Fallback to direct info lookup if search doesn't find exact match
                user_info = client.user_info_by_username(username)
                user_id = user_info.pk
                
        except Exception as e:
            # If both fail
            raise Exception(f"User @{username} lookup failed: {e}")
        
        # Small delay before sending
        random_delay(2, 5)
        
        # Send the message
        print(f"[*] Sending DM to @{username}...")
        result = client.direct_send(message, [user_id])
        
        if result:
            print(f"[✔] DM sent to @{username}")
            return True
        else:
            print(f"[!] Failed to send DM to @{username}")
            return False
            
    except Exception as e:
        err_msg = str(e).lower()
        if ("checkpoint" in err_msg or "challenge" in err_msg or "login" in err_msg) and retries > 0:
            print(f"[!] Hit security checkpoint. Attempting to resolve...")
            if resolve_challenge(client, e):
                print(f"[*] Retrying DM to @{username}...")
                return send_dm(client, username, message, retries=retries-1)
        
        print(f"[✘] Error sending DM to @{username}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Instagram DM Sender with Anti-Bot Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using existing session (safest):
  python dm_sender.py --session ../alissa.montez.session --targets targets.txt --message "Hey!"
  
  # Using username/password:
  python dm_sender.py -u myuser -p mypass --targets targets.txt --message "Hello!"
  
  # With proxy for extra safety:
  python dm_sender.py --session session.json --targets targets.txt --message "Hi!" --proxy http://user:pass@proxy:port
  
  # Single user (no targets file):
  python dm_sender.py --session session.json --to targetuser --message "Hey there!"
        """
    )
    
    # Authentication options
    auth_group = parser.add_argument_group('Authentication')
    auth_group.add_argument('-u', '--username', help='Instagram username')
    auth_group.add_argument('-p', '--password', help='Instagram password')
    auth_group.add_argument('--session', help='Path to session file (preferred)')
    
    # Target options
    target_group = parser.add_argument_group('Targets')
    target_group.add_argument('--targets', help='Path to targets.txt file')
    target_group.add_argument('--to', help='Single username to message')
    
    # Message options
    msg_group = parser.add_argument_group('Message')
    msg_group.add_argument('-m', '--message', help='Message to send')
    msg_group.add_argument('--count', type=int, default=1, help='Number of times to send (default: 1)')
    
    # Anti-detection options
    safety_group = parser.add_argument_group('Anti-Detection')
    safety_group.add_argument('--proxy', help='Proxy URL (http://user:pass@host:port)')
    safety_group.add_argument('--min-delay', type=float, default=5.0, help='Min delay between messages (default: 5s)')
    safety_group.add_argument('--max-delay', type=float, default=15.0, help='Max delay between messages (default: 15s)')
    
    # Other options
    parser.add_argument('--non-interactive', action='store_true', help='Run without user prompts')
    parser.add_argument('--allow-password-fallback', action='store_true',
                        help='Allow username/password fallback if session fails')
    parser.add_argument('--challenge-only', action='store_true',
                        help='Attempt login and print challenge payload, then exit')
    parser.add_argument('--use-default-device', action='store_true',
                        help='Use instagrapi default device/user agent settings (default)')
    parser.add_argument('--force-custom-device', action='store_true',
                        help='Force custom device/user agent settings')
    parser.add_argument('--strip-session-device', action='store_true',
                        help='Remove device_settings/user_agent from session file before loading')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without sending')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.session and not (args.username and args.password):
        print("[!] Error: Provide --session file OR --username and --password")
        parser.print_help()
        sys.exit(1)
    
    if not args.targets and not args.to:
        print("[!] Error: Provide --targets file OR --to username")
        parser.print_help()
        sys.exit(1)
    
    if not args.message:
        if args.non_interactive:
            print("[!] Error: --message required in non-interactive mode")
            sys.exit(1)
        args.message = input("[?] Enter message to send: ").strip()
        if not args.message:
            print("[!] Error: Message cannot be empty")
            sys.exit(1)
    
    # Get targets
    if args.to:
        targets = [args.to]
    else:
        targets = load_targets(args.targets)
        if not targets:
            print("[!] Error: No targets found")
            sys.exit(1)
    
    # Dry run mode
    if args.dry_run:
        print("\n[DRY RUN] Would send the following:")
        print(f"  Message: {args.message}")
        print(f"  Count: {args.count}")
        print(f"  Targets: {', '.join(targets)}")
        print(f"  Total messages: {len(targets) * args.count}")
        sys.exit(0)
    
    # Confirmation
    if not args.non_interactive:
        print(f"\n[*] About to send {args.count} message(s) to {len(targets)} user(s)")
        print(f"[*] Message: {args.message[:50]}{'...' if len(args.message) > 50 else ''}")
        confirm = input("[?] Continue? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("[*] Cancelled.")
            sys.exit(0)
    
    # Setup client with anti-detection
    use_default_device = True if args.use_default_device or not args.force_custom_device else False
    client = setup_client(proxy=args.proxy, use_default_device=use_default_device)
    
    # Authenticate
    logged_in = False
    
    # 1. Try loading session
    session_result = False
    if args.session:
        session_result = load_session(client, args.session, strip_device_settings=args.strip_session_device)
        logged_in = session_result is True
    
    # 2. Try credentials from args or .env
    if not logged_in:
        if args.challenge_only and session_result == "challenge":
            print_challenge_payload(client)
            sys.exit(0)

        if session_result == "challenge" and not args.allow_password_fallback:
            print("[!] Session requires a challenge. Skipping password fallback to avoid extra login attempts.")
            print("[!] Re-run with --allow-password-fallback if you want to force a login attempt.")
            sys.exit(1)

        username = args.username
        password = args.password

        # Pull from .env only when fallback is explicitly allowed or no session was used.
        if not username or not password:
            if args.allow_password_fallback or not args.session:
                creds = load_env_credentials()
                username = username or creds["username"]
                password = password or creds["password"]

        if username and password:
            print(f"[*] Falling back to fresh credentials login for @{username}...")
            # Create a fresh client to avoid session contamination
            client = setup_client(proxy=args.proxy, use_default_device=use_default_device)
            session_file = args.session or f"{username}.session.json"
            logged_in = login_with_password(client, username, password, session_file)
            if args.challenge_only and not logged_in:
                print_challenge_payload(client)
                sys.exit(0)
    
    if not logged_in:
        print("[✘] Failed to authenticate. Exiting.")
        sys.exit(1)
    
    # Send messages
    success_count = 0
    fail_count = 0
    
    print(f"\n[*] Starting to send messages...")
    print(f"[*] Delay between messages: {args.min_delay}-{args.max_delay}s")
    
    for i in range(args.count):
        if args.count > 1:
            print(f"\n--- Round {i+1}/{args.count} ---")
        
        for target in targets:
            if send_dm(client, target, args.message):
                success_count += 1
            else:
                fail_count += 1
            
            # Add delay between messages (anti-detection)
            if target != targets[-1] or i < args.count - 1:
                random_delay(args.min_delay, args.max_delay)
    
    # Summary
    print(f"\n{'='*40}")
    print(f"[*] SUMMARY")
    print(f"[✔] Sent: {success_count}")
    print(f"[✘] Failed: {fail_count}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
