#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI configuration for EliteXV8.py
"""

import os
from dotenv import load_dotenv

# Load Azure environment variables
load_dotenv(dotenv_path=".envAzure")

print("="*80)
print("🔍 TESTING AZURE OPENAI CONFIGURATION FOR ELITEXV8".center(80))
print("="*80 + "\n")

# Check all required environment variables
required_vars = {
    "AZURE_OPENAI_API_KEY": "API Key",
    "AZURE_OPENAI_ENDPOINT": "Endpoint URL",
    "AZURE_OPENAI_DEPLOYMENT": "Deployment Name",
    "AZURE_OPENAI_API_VERSION": "API Version",
    "AZURE_OPENAI_MODEL": "Model Name"
}

print("📋 Environment Variables Check:")
print("-" * 80)
all_present = True
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        # Mask API key for security
        if "KEY" in var:
            display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        else:
            display_value = value
        print(f"✅ {var:<30} = {display_value}")
    else:
        print(f"❌ {var:<30} = NOT SET")
        all_present = False

print("-" * 80)

if not all_present:
    print("\n❌ Missing required environment variables in .envAzure file!")
    exit(1)

print("\n✅ All required environment variables are set!\n")

# Test Azure OpenAI connection
print("="*80)
print("🧪 TESTING AZURE OPENAI CONNECTION".center(80))
print("="*80 + "\n")

try:
    from openai import AzureOpenAI
    
    client = AzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )
    
    print("🔄 Sending test request to Azure OpenAI...")
    
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": "Say 'Azure OpenAI connection successful!' in exactly 5 words."}
        ],
        max_tokens=50,
        temperature=0.7
    )
    
    result = response.choices[0].message.content
    
    print("\n" + "="*80)
    print("✅ CONNECTION SUCCESSFUL!")
    print("="*80)
    print(f"\n📝 Response from {os.getenv('AZURE_OPENAI_MODEL')}:")
    print(f"   └─ {result}\n")
    
    print("📊 Response Details:")
    print(f"   └─ Model: {response.model}")
    print(f"   └─ Tokens Used: {response.usage.total_tokens}")
    print(f"   └─ Completion Tokens: {response.usage.completion_tokens}")
    print(f"   └─ Prompt Tokens: {response.usage.prompt_tokens}\n")
    
    print("="*80)
    print("🎉 EliteXV8 is ready to use Azure OpenAI GPT-4o!".center(80))
    print("="*80 + "\n")
    
except Exception as e:
    print("\n" + "="*80)
    print("❌ CONNECTION FAILED!")
    print("="*80)
    print(f"\n🔴 Error: {str(e)}\n")
    print("💡 Troubleshooting:")
    print("   1. Check if .envAzure file exists")
    print("   2. Verify Azure OpenAI credentials are correct")
    print("   3. Ensure deployment name matches in Azure portal")
    print("   4. Check if API version is supported\n")
    exit(1)

