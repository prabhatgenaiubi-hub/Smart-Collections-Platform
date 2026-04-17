import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

print("=== Checking SarvamAI client structure ===\n")
print("Main client attributes:")
print(dir(client))
print("\n" + "="*50 + "\n")

print("speech_to_text attributes:")
print(dir(client.speech_to_text))
print("\n" + "="*50 + "\n")

print("text attributes:")
print(dir(client.text))
