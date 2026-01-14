#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Followers Extractor
Extracts followers from specified Instagram users and saves to JSON/CSV
"""

import sys
import json
import csv
import argparse
import os
from pathlib import Path
from datetime import datetime

try:
    import instaloader
    from colorama import init, Fore
except ImportError as e:
    print(f"[X] Error: Missing required package: {e}")
    print("[+] Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

init(autoreset=True)
GREEN = Fore.GREEN
RED = Fore.RED
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN

def configure_proxy():
    """
    Configure proxy settings from environment variables.
    The requests library (used by instaloader) respects HTTP_PROXY, HTTPS_PROXY environment variables.
    """
    proxy_host = os.getenv('PROXY_HOST')
    proxy_port = os.getenv('PROXY_PORT')
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_protocol = os.getenv('PROXY_PROTOCOL', 'http').lower()
    
    if not proxy_host or not proxy_port:
        return  # No proxy configuration
    
    # Build proxy URL
    if proxy_username and proxy_password:
        proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
    else:
        proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
    
    # Set environment variables that requests library respects
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url
    
    print(f"{CYAN}[*] Proxy configured: {proxy_protocol}://{proxy_host}:{proxy_port}")

def extract_followers(username: str, session_file: str, output_format: str = 'json', output_file: str = None, limit: int = None):
    """
    Extract followers from an Instagram user
    
    Args:
        username: Instagram username to extract followers from
        session_file: Path to Instagram session file
        output_format: Output format ('json' or 'csv')
        output_file: Output file path (optional, will auto-generate if not provided)
    """
    try:
        # Configure proxy if environment variables are set
        configure_proxy()
        
        # Initialize Instaloader
        loader = instaloader.Instaloader()
        
        # Load session if provided
        if session_file:
            # Find the session file - check multiple locations
            session_base = session_file
            if session_base.endswith('.session'):
                session_base = session_base[:-8]
            
            instatools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            session_paths = [
                os.path.join(os.getcwd(), session_base),
                os.path.join(os.getcwd(), session_base + '.session'),
                os.path.join(instatools_dir, session_base),
                os.path.join(instatools_dir, session_base + '.session'),
            ]
            
            session_found = None
            for path in session_paths:
                if os.path.exists(path):
                    session_found = path
                    break
            
            if session_found:
                # Instaloader expects session files in a specific temp directory
                # Copy the session file to where instaloader expects it
                import tempfile
                import shutil
                
                session_name = os.path.basename(session_found)
                if session_name.endswith('.session'):
                    session_name = session_name[:-8]
                
                # Get instaloader's expected session directory
                temp_dir = tempfile.gettempdir()
                system_username = os.getenv('USER', os.getenv('USERNAME', 'user'))
                instaloader_session_dir = os.path.join(temp_dir, f'.instaloader-{system_username}')
                os.makedirs(instaloader_session_dir, exist_ok=True)
                
                # Copy session file to instaloader's directory
                target_session = os.path.join(instaloader_session_dir, f'session-{session_name}')
                try:
                    shutil.copy2(session_found, target_session)
                    loader.load_session_from_file(session_name)
                    print(f"{GREEN}[OK] Session loaded from {session_found}")
                except Exception as e:
                    # Try direct path loading as fallback
                    try:
                        loader.load_session_from_file(os.path.abspath(session_found))
                        print(f"{GREEN}[OK] Session loaded from {session_found}")
                    except Exception as e2:
                        print(f"{YELLOW}[!] Warning: Could not load session: {e2}")
            else:
                print(f"{YELLOW}[!] Warning: Session file not found at {session_file}. May have limited access to private profiles.")
        else:
            print(f"{YELLOW}[!] Warning: No session file provided. May have limited access to private profiles.")
        
        # Load profile (explicitly use the requested username)
        print(f"{CYAN}[*] Loading profile for @{username}...")
        # Profile.from_username should work regardless of session username, but let's be explicit
        profile = instaloader.Profile.from_username(loader.context, username)
        print(f"{GREEN}[OK] Profile loaded: {profile.full_name} (@{profile.username})")
        print(f"{CYAN}[*] Followers: {profile.followers}")
        
        # Extract followers
        print(f"{CYAN}[*] Extracting followers...")
        print(f"{CYAN}[*] This may take a while for accounts with many followers...")
        followers = []
        follower_count = 0
        total_followers = profile.followers
        
        try:
            for follower in profile.get_followers():
                follower_data = {
                    'username': follower.username,
                    'full_name': follower.full_name,
                    'user_id': follower.userid,
                    'is_verified': follower.is_verified,
                    'is_private': follower.is_private,
                    'profile_pic_url': follower.profile_pic_url,
                    'biography': follower.biography,
                    'followers': follower.followers,
                    'followees': follower.followees,
                    'profile_url': f"https://instagram.com/{follower.username}/"
                }
                followers.append(follower_data)
                follower_count += 1
                
                # Show progress more frequently for large accounts
                if follower_count % 50 == 0:
                    progress_pct = (follower_count / total_followers * 100) if total_followers > 0 else 0
                    print(f"\n{CYAN}[*] Extracted {follower_count}/{total_followers} followers ({progress_pct:.1f}%)...")
                elif follower_count % 10 == 0:
                    # Less verbose updates every 10
                    sys.stdout.write(f"\r{CYAN}[*] Extracting... {follower_count} followers so far")
                    sys.stdout.flush()
                
                # Stop if limit is reached
                if limit and follower_count >= limit:
                    print(f"\n{YELLOW}[!] Reached limit of {limit} followers. Stopping extraction.")
                    break
                    
        except Exception as e:
            print(f"{RED}[✘] Error extracting followers: {e}")
            if "login" in str(e).lower() or "private" in str(e).lower():
                print(f"{YELLOW}[!] This profile may be private. Please ensure you're logged in with a session file.")
            raise
        
        print(f"{GREEN}[OK] Successfully extracted {len(followers)} followers!")
        
        # Determine output file
        if not output_file:
            output_file = f"followers_{username}.{output_format}"
        
        # Save to file
        output_path = Path(output_file)
        print(f"{CYAN}[*] Saving to {output_path}...")
        
        if output_format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'target_username': username,
                    'target_full_name': profile.full_name,
                    'total_followers': len(followers),
                    'extracted_at': datetime.now().isoformat(),
                    'followers': followers
                }, f, indent=2, ensure_ascii=False)
        elif output_format.lower() == 'csv':
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if followers:
                    writer = csv.DictWriter(f, fieldnames=followers[0].keys())
                    writer.writeheader()
                    writer.writerows(followers)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        print(f"{GREEN}[OK] Saved {len(followers)} followers to {output_path}")
        return output_path, followers
        
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"{RED}[X] Error: Profile @{username} does not exist")
        sys.exit(1)
    except instaloader.exceptions.LoginRequiredException:
        print(f"{RED}[X] Error: Login required. Please provide a valid session file.")
        print(f"{YELLOW}[+] Run: python3 cookies.py to create a session file")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}[X] Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Extract followers from Instagram users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 followers_extractor.py -u target_username -s session_file
  python3 followers_extractor.py -u target_username -s session_file -f csv -o output.csv
  python3 followers_extractor.py -u user1 -u user2 -s session_file
        """
    )
    
    parser.add_argument(
        '-u', '--username',
        action='append',
        required=True,
        help='Instagram username(s) to extract followers from (can be used multiple times)'
    )
    parser.add_argument(
        '-s', '--session',
        required=True,
        help='Path to Instagram session file (without .session extension)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: followers_<username>.<format>)'
    )
    parser.add_argument(
        '-l', '--limit',
        type=int,
        help='Limit the number of followers to extract (useful for testing or large accounts)'
    )
    
    args = parser.parse_args()
    
    results = {}
    
    for username in args.username:
        print(f"\n{'='*60}")
        print(f"{CYAN}[*] Processing @{username}")
        print(f"{'='*60}\n")
        
        output_file = args.output
        if not output_file and len(args.username) > 1:
            output_file = f"followers_{username}.{args.format}"
        
        try:
            output_path, followers = extract_followers(
                username=username,
                session_file=args.session,
                output_format=args.format,
                output_file=output_file,
                limit=args.limit
            )
            results[username] = {
                'output_file': str(output_path),
                'count': len(followers)
            }
        except Exception as e:
            print(f"{RED}[✘] Failed to extract followers from @{username}: {e}")
            results[username] = {'error': str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print(f"{GREEN}[OK] Extraction Summary")
    print(f"{'='*60}")
    for username, result in results.items():
        if 'error' in result:
            print(f"{RED}[✘] @{username}: {result['error']}")
        else:
            print(f"{GREEN}[OK] @{username}: {result['count']} followers saved to {result['output_file']}")


if __name__ == '__main__':
    main()

