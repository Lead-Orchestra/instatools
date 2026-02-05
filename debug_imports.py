import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    import instagrapi
    print(f"Instagrapi found at: {instagrapi.__file__}")
except ImportError as e:
    print(f"Instagrapi NOT found: {e}")

try:
    import instagrapi.exceptions
    print("Searching for Challenge/Checkpoint in instagrapi.exceptions:")
    for attr in dir(instagrapi.exceptions):
        if "Challenge" in attr or "Checkpoint" in attr or "Login" in attr:
            print(f"  {attr}")
except Exception as e:
    print(f"Failed to inspect instagrapi.exceptions: {e}")
