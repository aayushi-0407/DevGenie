import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configure API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env file")
    exit()

genai.configure(api_key=api_key)

print("🔍 Checking available models...")
print("=" * 50)

try:
    # List all available models
    models = genai.list_models()
    
    print("✅ Available models:")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"  • {model.name}")
    
    print("\n" + "=" * 50)
    print("💡 Look for models that support 'generateContent'")
    print("💡 Common model names include:")
    print("   - gemini-pro")
    print("   - gemini-pro-vision") 
    print("   - gemini-1.5-pro")
    print("   - gemini-1.5-flash")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Make sure your API key is valid and has the right permissions")
