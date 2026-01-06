# Followers Extractor 📊

A Python script to extract followers from Instagram users using the InstaTools framework.

## Features

- Extract followers from one or multiple Instagram users
- Export to JSON or CSV format
- Works with both public and private profiles (requires session file for private)
- Extracts comprehensive follower data including:
  - Username
  - Full name
  - User ID
  - Verification status
  - Privacy status
  - Profile picture URL
  - Biography
  - Follower/following counts
  - Profile URL

## Prerequisites

1. **Python 3.6+** installed
2. **InstaTools dependencies** installed:
   ```bash
   pip install -r ../../requirements.txt
   ```
3. **Instagram session file** created:
   ```bash
   python3 ../../cookies.py
   ```

## Usage

### Basic Usage

Extract followers from a single user:
```bash
python3 followers_extractor.py -u target_username -s session_file
```

### Multiple Users

Extract followers from multiple users:
```bash
python3 followers_extractor.py -u user1 -u user2 -u user3 -s session_file
```

### Output Formats

**JSON (default):**
```bash
python3 followers_extractor.py -u target_username -s session_file -f json
```

**CSV:**
```bash
python3 followers_extractor.py -u target_username -s session_file -f csv
```

### Custom Output File

```bash
python3 followers_extractor.py -u target_username -s session_file -o custom_output.json
```

## Arguments

- `-u, --username`: Instagram username(s) to extract followers from (can be used multiple times)
- `-s, --session`: Path to Instagram session file (without .session extension)
- `-f, --format`: Output format - `json` or `csv` (default: `json`)
- `-o, --output`: Output file path (optional, auto-generated if not provided)

## Output

### JSON Format

```json
{
  "target_username": "target_user",
  "target_full_name": "Target User",
  "total_followers": 1500,
  "extracted_at": "...",
  "followers": [
    {
      "username": "follower1",
      "full_name": "Follower One",
      "user_id": "123456789",
      "is_verified": false,
      "is_private": false,
      "profile_pic_url": "https://...",
      "biography": "Bio text",
      "followers": 500,
      "followees": 300,
      "profile_url": "https://instagram.com/follower1/"
    }
  ]
}
```

### CSV Format

The CSV file contains all follower data with columns:
- username
- full_name
- user_id
- is_verified
- is_private
- profile_pic_url
- biography
- followers
- followees
- profile_url

## Integration with TypeScript Backend

This script is designed to be called from the TypeScript backend wrapper:

```bash
pnpm scrape:instagram:followers -u target_user -s session_file
```

See `src/scraper-instagram-followers.ts` for the TypeScript wrapper implementation.

## Notes

- **Private Profiles**: Requires a valid session file to access private profiles
- **Rate Limiting**: Instagram may rate limit requests. The script includes delays to minimize this
- **Large Accounts**: Extracting followers from accounts with many followers may take significant time
- **Session Files**: Session files expire. You may need to regenerate them periodically

## Troubleshooting

### "Login required" Error

If you see a "Login required" error:
1. Make sure you've created a session file: `python3 ../../cookies.py`
2. Ensure you're logged into Instagram in Firefox
3. Try regenerating the session file

### "Profile does not exist" Error

- Verify the username is correct
- Check if the account is active
- Ensure you have access to the profile (for private accounts)

### Import Errors

If you see import errors:
```bash
pip install -r ../../requirements.txt
```

## License

Part of the InstaTools project. See the main repository for license information.

