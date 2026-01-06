from argparse import ArgumentParser
from glob import glob
from os.path import expanduser
from platform import system
from sqlite3 import OperationalError, connect

try:
    from instaloader import ConnectionException, Instaloader
except ModuleNotFoundError:
    raise SystemExit("Instaloader not found.\n  Run: pip install instaloader")


def has_instagram_cookies(cookiefile):
    """Check if a cookie file contains Instagram cookies."""
    try:
        conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM moz_cookies WHERE baseDomain='instagram.com'"
            ).fetchone()
            if result and result[0] > 0:
                return True
        except OperationalError:
            result = conn.execute(
                "SELECT COUNT(*) FROM moz_cookies WHERE host LIKE '%instagram.com'"
            ).fetchone()
            if result and result[0] > 0:
                return True
        conn.close()
    except Exception:
        pass
    return False


def get_cookiefile():
    """Get Firefox cookie file, checking both regular Firefox and Firefox Developer Edition."""
    platform = system()
    
    # Define all possible Firefox profile locations
    if platform == "Windows":
        cookie_patterns = [
            "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite",
            "~/AppData/Roaming/Mozilla/Firefox Developer Edition/Profiles/*/cookies.sqlite",
        ]
    elif platform == "Darwin":  # macOS
        cookie_patterns = [
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
            "~/Library/Application Support/Firefox Developer Edition/Profiles/*/cookies.sqlite",
        ]
    else:  # Linux
        cookie_patterns = [
            "~/.mozilla/firefox/*/cookies.sqlite",
            "~/.mozilla/firefox-developer-edition/*/cookies.sqlite",
        ]
    
    # Collect all cookie files from all locations
    all_cookiefiles = []
    for pattern in cookie_patterns:
        found_files = glob(expanduser(pattern))
        all_cookiefiles.extend(found_files)
    
    if not all_cookiefiles:
        error_msg = (
            "No Firefox cookies.sqlite file found in any of the following locations:\n"
        )
        for pattern in cookie_patterns:
            error_msg += f"  - {expanduser(pattern)}\n"
        error_msg += "\nMake sure you're logged into Instagram in Firefox or Firefox Developer Edition.\n"
        error_msg += "You can also specify a cookie file manually with: -c COOKIEFILE"
        raise SystemExit(error_msg)
    
    # If multiple cookie files found, prefer the one with Instagram cookies
    if len(all_cookiefiles) > 1:
        for cookiefile in all_cookiefiles:
            if has_instagram_cookies(cookiefile):
                return cookiefile
        # If none have Instagram cookies, return the first one (user can try manually)
        return all_cookiefiles[0]
    
    return all_cookiefiles[0]


def import_session(cookiefile, sessionfile):
    print(f"Using cookies from {cookiefile}.")
    conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
    try:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE baseDomain='instagram.com'"
        )
    except OperationalError:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        )
    instaloader = Instaloader(max_connection_attempts=1)
    instaloader.context._session.cookies.update(cookie_data)
    username = instaloader.test_login()
    if not username:
        raise SystemExit("Not logged in. Are you logged in successfully in Firefox?")
    print(f"Imported session cookie for {username}.")
    instaloader.context.username = username
    instaloader.save_session_to_file(sessionfile)


if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("-c", "--cookiefile")
    p.add_argument("-f", "--sessionfile")
    args = p.parse_args()
    try:
        import_session(args.cookiefile or get_cookiefile(), args.sessionfile)
    except (ConnectionException, OperationalError) as e:
        raise SystemExit(f"Cookie import failed: {e}")
