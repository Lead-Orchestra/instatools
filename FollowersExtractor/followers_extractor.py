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
import time
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
        
        # Initialize Instaloader with rate limit handling
        loader = instaloader.Instaloader(
            sleep=True,  # Enable automatic rate limit handling
            max_connection_attempts=3,
            request_timeout=300.0
        )
        
        # Configure context for better rate limit handling
        loader.context.max_connection_attempts = 3
        loader.context.request_timeout = 300.0
        
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
        partial_success = False
        
        # Rate limiting configuration
        delay_between_followers = float(os.getenv('INSTAGRAM_RATE_LIMIT_DELAY', '0.5'))  # Default 0.5s between followers
        delay_every_n_followers = int(os.getenv('INSTAGRAM_LONG_DELAY_INTERVAL', '100'))  # Every 100 followers
        long_delay_seconds = float(os.getenv('INSTAGRAM_LONG_DELAY', '5.0'))  # 5 second delay every N followers
        max_retries = int(os.getenv('INSTAGRAM_MAX_RETRIES', '3'))  # Max retries for 401 errors
        
        # Retry logic state
        consecutive_401_count = 0
        
        try:
            followers_iterator = profile.get_followers()
            
            while True:
                try:
                    # Get next follower with retry logic
                    retry_count = 0
                    follower = None
                    fetch_error = None
                    
                    while retry_count < max_retries:
                        try:
                            follower = next(followers_iterator)
                            consecutive_401_count = 0  # Reset on success
                            break
                        except StopIteration:
                            # End of followers
                            follower = None
                            break
                        except Exception as err:
                            error_msg = str(err).lower()
                            fetch_error = err
                            
                            # Check if it's a 401 error
                            is_401 = '401' in str(err) or 'unauthorized' in error_msg or 'login required' in error_msg
                            
                            if is_401:
                                consecutive_401_count += 1
                                
                                # Exponential backoff: 2^retry_count seconds
                                backoff_delay = min(2 ** retry_count, 60)  # Cap at 60 seconds
                                
                                # Additional delay if multiple consecutive 401s
                                if consecutive_401_count > 1:
                                    backoff_delay *= consecutive_401_count
                                
                                # If we have followers, save partial results and continue with longer delay
                                if len(followers) > 0:
                                    print(f"\n{YELLOW}[!] HTTP 401 error encountered ({consecutive_401_count} consecutive). Rate limited?")
                                    print(f"{YELLOW}[!] Backing off for {backoff_delay:.1f} seconds... (Have {len(followers)} followers so far)")
                                    
                                    # Save partial results before retrying
                                    partial_success = True
                                    try:
                                        temp_output_file = output_file or f"followers_{username}.{output_format}"
                                        if output_format.lower() == 'json':
                                            temp_path = Path(temp_output_file)
                                            with open(temp_path, 'w', encoding='utf-8') as f:
                                                json.dump({
                                                    'target_username': username,
                                                    'target_full_name': profile.full_name,
                                                    'total_followers': len(followers),
                                                    'extracted_at': datetime.now().isoformat(),
                                                    'partial': True,
                                                    'followers': followers
                                                }, f, indent=2, ensure_ascii=False)
                                            print(f"{GREEN}[OK] Partial results saved ({len(followers)} followers)")
                                    except Exception as save_error:
                                        print(f"{YELLOW}[!] Could not save partial results: {save_error}")
                                
                                time.sleep(backoff_delay)
                                retry_count += 1
                                
                                # If we've exhausted retries and have no followers, fail
                                if retry_count >= max_retries and len(followers) == 0:
                                    print(f"{RED}[✘] Max retries reached with no followers collected. Giving up.")
                                    raise
                                
                                # If we've exhausted retries but have followers, save and exit gracefully
                                if retry_count >= max_retries:
                                    print(f"{YELLOW}[!] Max retries reached. Saving {len(followers)} collected followers as partial result.")
                                    partial_success = True
                                    break
                            else:
                                # Non-401 error, re-raise immediately
                                raise
                        
                    # If we couldn't get a follower after retries, break the loop
                    if follower is None:
                        if retry_count >= max_retries and len(followers) > 0:
                            # Partial success - we'll save results outside the loop
                            break
                        elif retry_count >= max_retries:
                            # Complete failure
                            if fetch_error:
                                raise fetch_error
                            break
                        else:
                            # Normal end of iteration
                            break
                    
                    # Extract follower data
                    try:
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
                        
                        # Rate limiting: small delay between followers
                        if delay_between_followers > 0:
                            time.sleep(delay_between_followers)
                        
                        # Rate limiting: longer delay every N followers
                        if delay_every_n_followers > 0 and follower_count % delay_every_n_followers == 0:
                            print(f"\n{YELLOW}[!] Pausing {long_delay_seconds}s to avoid rate limits ({follower_count} followers collected)...")
                            time.sleep(long_delay_seconds)
                        
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
                            
                    except Exception as process_error:
                        # Error processing individual follower, log and continue
                        print(f"\n{YELLOW}[!] Error processing follower: {process_error}")
                        print(f"{YELLOW}[!] Continuing with next follower...")
                        continue
                        
                except StopIteration:
                    # Normal end of followers
                    break
                    
        except Exception as e:
            error_msg = str(e).lower()
            is_401 = '401' in str(e) or 'unauthorized' in error_msg or 'login required' in error_msg
            
            # If we have followers collected, save them before failing
            if len(followers) > 0:
                print(f"\n{RED}[✘] Error extracting followers: {e}")
                print(f"{YELLOW}[!] Saving {len(followers)} collected followers as partial result...")
                partial_success = True
                
                # Save partial results
                try:
                    temp_output_file = output_file or f"followers_{username}.{output_format}"
                    temp_path = Path(temp_output_file)
                    if output_format.lower() == 'json':
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'target_username': username,
                                'target_full_name': profile.full_name,
                                'total_followers': len(followers),
                                'extracted_at': datetime.now().isoformat(),
                                'partial': True,
                                'error': str(e),
                                'followers': followers
                            }, f, indent=2, ensure_ascii=False)
                        print(f"{GREEN}[OK] Partial results saved to {temp_path}")
                    # Don't re-raise if we saved partial results and it's a 401
                    if is_401:
                        print(f"{YELLOW}[!] Continuing with partial results due to 401 error (likely rate limiting)")
                        # Don't re-raise, allow partial success
                    else:
                        raise  # Re-raise non-401 errors
                except Exception as save_error:
                    print(f"{RED}[✘] Could not save partial results: {save_error}")
                    raise  # Re-raise if we couldn't save
            else:
                # No followers collected, fail normally
                print(f"{RED}[✘] Error extracting followers: {e}")
                if "login" in error_msg or "private" in error_msg or is_401:
                    print(f"{YELLOW}[!] This may be due to rate limiting or session expiration.")
                    print(f"{YELLOW}[!] Please ensure you're logged in with a valid session file.")
                raise
        
        # Determine output file
        if not output_file:
            output_file = f"followers_{username}.{output_format}"
        
        # Save to file (only if not already saved as partial)
        output_path = Path(output_file)
        if not partial_success or not output_path.exists():
            print(f"{CYAN}[*] Saving to {output_path}...")
            
            if output_format.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'target_username': username,
                        'target_full_name': profile.full_name,
                        'total_followers': len(followers),
                        'extracted_at': datetime.now().isoformat(),
                        'partial': partial_success,
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
        else:
            print(f"{GREEN}[OK] Partial results already saved to {output_path}")
        
        if partial_success:
            print(f"{YELLOW}[!] Partial extraction completed: {len(followers)} followers saved (may have been interrupted by rate limiting)")
        else:
            print(f"{GREEN}[OK] Successfully extracted {len(followers)} followers!")
        
        print(f"{GREEN}[OK] Saved {len(followers)} followers to {output_path}")
        return output_path, followers, partial_success
        
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
            result = extract_followers(
                username=username,
                session_file=args.session,
                output_format=args.format,
                output_file=output_file,
                limit=args.limit
            )
            
            # Handle both old format (2 values) and new format (3 values)
            if len(result) == 3:
                output_path, followers, partial = result
            else:
                output_path, followers = result
                partial = False
            
            results[username] = {
                'output_file': str(output_path),
                'count': len(followers),
                'partial': partial
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
            partial_marker = " (partial)" if result.get('partial', False) else ""
            print(f"{GREEN}[OK] @{username}: {result['count']} followers saved to {result['output_file']}{partial_marker}")


if __name__ == '__main__':
    main()

