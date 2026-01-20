#!/usr/bin/env python3
"""
Strava Webhook Subscription Manager for SweatBet.

This script manages your Strava webhook subscription:
- View existing subscriptions
- Create a new subscription
- Delete existing subscription

Usage:
    python scripts/manage_webhook.py [view|create|delete]

Prerequisites:
    - Your SweatBet app must be deployed and publicly accessible
    - Environment variables must be set (see .env.example)

You can only have ONE subscription per Strava application.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Strava API endpoint for push subscriptions
STRAVA_SUBSCRIPTION_URL = "https://www.strava.com/api/v3/push_subscriptions"


def get_config():
    """Get required configuration from environment variables."""
    config = {
        "client_id": os.getenv("STRAVA_CLIENT_ID"),
        "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
        "verify_token": os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN", "SWEATBET_WEBHOOK_TOKEN"),
        "callback_url": os.getenv("STRAVA_WEBHOOK_CALLBACK_URL"),
    }
    
    # Validate required fields
    missing = [k for k, v in config.items() if not v and k != "verify_token"]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nRequired variables:")
        print("  STRAVA_CLIENT_ID - Your Strava app's client ID")
        print("  STRAVA_CLIENT_SECRET - Your Strava app's client secret")
        print("  STRAVA_WEBHOOK_CALLBACK_URL - Your public webhook URL")
        print("    Example: https://your-app.railway.app/webhooks/strava")
        print("\nOptional:")
        print("  STRAVA_WEBHOOK_VERIFY_TOKEN - Your verify token (default: SWEATBET_WEBHOOK_TOKEN)")
        sys.exit(1)
    
    return config


async def view_subscription():
    """
    View your current webhook subscription.
    
    Returns the subscription details if one exists.
    """
    config = get_config()
    
    print("\n📋 Checking existing webhook subscriptions...\n")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            STRAVA_SUBSCRIPTION_URL,
            params={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"]
            }
        )
    
    if response.status_code == 200:
        subscriptions = response.json()
        
        if subscriptions:
            print("✅ Active subscription found:\n")
            for sub in subscriptions:
                print(f"   Subscription ID: {sub.get('id')}")
                print(f"   Callback URL:    {sub.get('callback_url')}")
                print(f"   Created:         {sub.get('created_at', 'N/A')}")
                print(f"   Updated:         {sub.get('updated_at', 'N/A')}")
            return subscriptions
        else:
            print("📭 No active subscriptions found.")
            print("   Run 'python scripts/manage_webhook.py create' to create one.")
            return []
    else:
        print(f"❌ Failed to fetch subscriptions")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


async def create_subscription():
    """
    Create a new webhook subscription with Strava.
    
    Prerequisites:
    1. Your callback URL must be publicly accessible
    2. Your callback endpoint must be running and responding
    3. You can only have ONE subscription per app
    """
    config = get_config()
    
    print("\n🚀 Creating webhook subscription...\n")
    print(f"   Callback URL: {config['callback_url']}")
    print(f"   Verify Token: {config['verify_token']}")
    print()
    
    # First, check if a subscription already exists
    async with httpx.AsyncClient() as client:
        # Check existing
        check_response = await client.get(
            STRAVA_SUBSCRIPTION_URL,
            params={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"]
            }
        )
        
        if check_response.status_code == 200:
            existing = check_response.json()
            if existing:
                print("⚠️  A subscription already exists!")
                print(f"   ID: {existing[0].get('id')}")
                print(f"   URL: {existing[0].get('callback_url')}")
                print("\n   Delete it first with: python scripts/manage_webhook.py delete")
                return None
        
        # Create new subscription
        response = await client.post(
            STRAVA_SUBSCRIPTION_URL,
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "callback_url": config["callback_url"],
                "verify_token": config["verify_token"]
            }
        )
    
    if response.status_code == 201:
        data = response.json()
        print("✅ Subscription created successfully!\n")
        print(f"   Subscription ID: {data.get('id')}")
        print("\n   Your webhook is now active and will receive events from Strava.")
        print("   Complete an activity to test it!")
        return data
    elif response.status_code == 409:
        print("⚠️  A subscription already exists for this application.")
        print("   Delete it first with: python scripts/manage_webhook.py delete")
        return None
    else:
        print(f"❌ Failed to create subscription")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print("\n   Common issues:")
        print("   - Your callback URL is not publicly accessible")
        print("   - Your webhook endpoint is not responding correctly")
        print("   - The verify token doesn't match between script and server")
        return None


async def delete_subscription(subscription_id: int = None):
    """
    Delete a webhook subscription.
    
    If no subscription_id is provided, deletes the first (and usually only) subscription.
    """
    config = get_config()
    
    # If no ID provided, fetch the current subscription
    if subscription_id is None:
        print("\n🔍 Finding subscription to delete...\n")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                STRAVA_SUBSCRIPTION_URL,
                params={
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"]
                }
            )
        
        if response.status_code == 200:
            subscriptions = response.json()
            if subscriptions:
                subscription_id = subscriptions[0].get('id')
                print(f"   Found subscription ID: {subscription_id}")
            else:
                print("📭 No subscriptions found to delete.")
                return False
        else:
            print(f"❌ Failed to fetch subscriptions: {response.text}")
            return False
    
    print(f"\n🗑️  Deleting subscription {subscription_id}...\n")
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{STRAVA_SUBSCRIPTION_URL}/{subscription_id}",
            params={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"]
            }
        )
    
    if response.status_code == 204:
        print(f"✅ Subscription {subscription_id} deleted successfully!")
        print("\n   You can now create a new subscription with a different callback URL.")
        return True
    else:
        print(f"❌ Failed to delete subscription")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


async def test_verification():
    """
    Test if your webhook verification endpoint is working correctly.
    
    Simulates Strava's verification request to your callback URL.
    """
    config = get_config()
    
    if not config["callback_url"]:
        print("❌ STRAVA_WEBHOOK_CALLBACK_URL not set")
        return False
    
    print("\n🧪 Testing webhook verification endpoint...\n")
    print(f"   URL: {config['callback_url']}")
    print()
    
    test_challenge = "test_challenge_12345"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                config["callback_url"],
                params={
                    "hub.mode": "subscribe",
                    "hub.challenge": test_challenge,
                    "hub.verify_token": config["verify_token"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                returned_challenge = data.get("hub.challenge")
                
                if returned_challenge == test_challenge:
                    print("✅ Verification endpoint is working correctly!")
                    print(f"   Challenge echoed: {returned_challenge}")
                    return True
                else:
                    print(f"❌ Challenge mismatch!")
                    print(f"   Expected: {test_challenge}")
                    print(f"   Got: {returned_challenge}")
                    return False
            else:
                print(f"❌ Verification failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except httpx.ConnectError:
            print("❌ Could not connect to your callback URL")
            print("   Make sure your app is deployed and running")
            return False
        except Exception as e:
            print(f"❌ Error testing endpoint: {str(e)}")
            return False


def print_usage():
    """Print usage instructions."""
    print("""
Strava Webhook Subscription Manager
====================================

Usage:
    python scripts/manage_webhook.py <command>

Commands:
    view    - View your current webhook subscription
    create  - Create a new webhook subscription
    delete  - Delete your existing subscription
    test    - Test if your verification endpoint is working

Examples:
    python scripts/manage_webhook.py view
    python scripts/manage_webhook.py create
    python scripts/manage_webhook.py delete
    python scripts/manage_webhook.py test

Environment Variables Required:
    STRAVA_CLIENT_ID            - Your Strava app's client ID
    STRAVA_CLIENT_SECRET        - Your Strava app's client secret
    STRAVA_WEBHOOK_CALLBACK_URL - Your public webhook URL
                                  (e.g., https://your-app.railway.app/webhooks/strava)
    STRAVA_WEBHOOK_VERIFY_TOKEN - Your verify token (default: SWEATBET_WEBHOOK_TOKEN)
""")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "view":
        await view_subscription()
    elif command == "create":
        await create_subscription()
    elif command == "delete":
        # Optional: accept subscription ID as argument
        sub_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        await delete_subscription(sub_id)
    elif command == "test":
        await test_verification()
    elif command in ["help", "-h", "--help"]:
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

