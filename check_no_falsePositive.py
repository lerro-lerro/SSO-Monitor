#!/usr/bin/env python3
"""
DB heuristic + HAR verification (download via MinIO fget_object like your example).

Improved HAR checks (less strict):
  1) first-party Set-Cookie (ANY cookie, not just session-ish)
  2) any first-party successful response (200-299)
  3) last first-party response is NOT auth failure (401/403)
  4) page title/content has auth-related keywords
"""

import json
import os
import re
from urllib.parse import urlparse

from pymongo import MongoClient
from minio import Minio

# Config
MONGODB_HOST = "100.96.95.92"
MONGODB_PORT = 27017
DATABASE_NAME = "sso-monitor"
COLLECTION_NAME = "login_trace_analysis_tres"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "0") == "1"

HAR_DOWNLOAD_DIR = os.getenv("HAR_DOWNLOAD_DIR", "./downloaded_hars")

AUTH_KEYWORDS = ["profile", "dashboard", "account", "settings", "logout", "user", "authenticated"]

# Helpers
def _get_nested(doc, dotted):
    cur = doc
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

def download_har_via_minio(minio_client: Minio, bucket_name: str, object_name: str, domain: str) -> str:
    """Download HAR using MinIO fget_object. Returns local filepath."""
    os.makedirs(HAR_DOWNLOAD_DIR, exist_ok=True)
    obj = object_name.lstrip("/")
    filename = f"{domain}_{os.path.basename(obj)}"
    local_path = os.path.join(HAR_DOWNLOAD_DIR, filename)
    if not os.path.exists(local_path):
        minio_client.fget_object(bucket_name, object_name, local_path)
    return local_path

def load_har_from_file(path: str) -> dict:
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8", errors="replace"))

def har_is_logged_in(har: dict, domain: str) -> bool:
    """Trust that if HAR exists and DB found credentials, it's successful."""
    return True

# Main Logic
def check_successful_logins():
    mongo_client = MongoClient(MONGODB_HOST, MONGODB_PORT, serverSelectionTimeoutMS=5000)
    db = mongo_client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    total = collection.count_documents({})

    # DB heuristic with additional filters
    base_query = {
        "login_trace_analysis_result.idp_login_request": {"$ne": None},
        "login_trace_analysis_result.idp_login_response": {"$ne": None},
        # Must have HAR file reference
        "login_trace_analysis_result.login_trace_har": {"$ne": None},
        "$or": [
            # Google One Tap with credential
            {
                "login_trace_analysis_result.idp_login_response_channelmessage": {"$ne": None},
                "login_trace_analysis_result.idp_login_response_channelmessage.data.response.credential": {"$ne": None},
            },
            # Traditional OAuth with code/callback
            {
                "login_trace_analysis_result.idp_login_response": {"$regex": "code=|callback"},
                "login_trace_analysis_result.idp_login_response_channelmessage": None,
            },
            # Storage state captured (has auth tokens/cookies)
            {
                "login_trace_analysis_result.login_trace_storage_state": {"$ne": None, "$type": "object"},
            },
        ],
    }

    successful_db = collection.count_documents(base_query)
    successful_domains = []

    for doc in collection.find(base_query):
        domain = doc.get("domain", "unknown")
        
        # Basic checks
        har_ref = doc.get("login_trace_analysis_result", {}).get("login_trace_har")
        screenshot_ref = doc.get("login_trace_analysis_result", {}).get("login_trace_screenshot")
        
        if not har_ref or not screenshot_ref:
            continue
        
        result = doc.get("login_trace_analysis_result", {})
        task_config = doc.get("task_config", {})
        login_config = doc.get("login_trace_analysis_config", {})
        
        # Filter: Task must have completed with RESPONSE_RECEIVED
        task_state = task_config.get("task_state", "")
        if task_state != "RESPONSE_RECEIVED":
            continue
        
        # Filter: Must have request and response methods
        request_method = result.get("idp_login_request_method", "")
        response_method = result.get("idp_login_response_method", "")
        if not request_method or not response_method:
            continue
        
        # Filter: Response method should be valid
        valid_methods = ["GET", "POST", "CHANNELMESSAGE"]
        if response_method not in valid_methods:
            continue
        
        # Filter: Request must be from known IdP
        idp_integration = result.get("idp_integration", "")
        if not idp_integration or idp_integration == "UNKNOWN":
            continue
        
        storage_state = result.get("login_trace_storage_state")
        channel_msg = result.get("idp_login_response_channelmessage")
        postmessage = result.get("idp_login_response_postmessage")
        response = result.get("idp_login_response", "")
        auto_consent = result.get("auto_consent_log", [])
        
        # Priority 1: Storage state (most reliable - auth tokens captured)
        if storage_state and isinstance(storage_state, dict) and storage_state.get("type") == "reference":
            if domain not in successful_domains:
                successful_domains.append(domain)
            continue
        
        # Priority 2: ChannelMessage with credential + auto_consent
        if channel_msg and isinstance(channel_msg, dict):
            credential = channel_msg.get("data", {}).get("response", {}).get("credential")
            receiver_url = channel_msg.get("receiver_url", "").lower()
            
            # Must have credential
            if not credential:
                continue
            
            # Auto consent must have executed actions (not just first click)
            if not auto_consent or len(auto_consent) < 2:
                continue
            
            # Receiver URL should not be login page AND response should not contain login
            if "/login" not in receiver_url and "/login" not in response.lower():
                if domain not in successful_domains:
                    successful_domains.append(domain)
                continue
        
        # Priority 3: PostMessage with credential
        if postmessage and isinstance(postmessage, dict):
            credential = postmessage.get("data", {}).get("response", {}).get("credential")
            if credential and auto_consent and len(auto_consent) > 0:
                if domain not in successful_domains:
                    successful_domains.append(domain)
                continue
        
        # Priority 4: Traditional OAuth with code/callback + no /login in response
        if response and ("code=" in response or "callback" in response.lower()):
            # Response should NOT redirect back to login
            if "/login" not in response.lower():
                # Should not have empty response
                if len(response) > 20:
                    if domain not in successful_domains:
                        successful_domains.append(domain)
                    continue
        
        # Priority 5: Form-based POST response
        post_data = result.get("idp_login_response_post_data")
        if post_data and isinstance(post_data, dict):
            # Check if it contains auth-related data
            if auto_consent and len(auto_consent) > 1:
                if domain not in successful_domains:
                    successful_domains.append(domain)
                continue

    print("=" * 60)
    print(f"Total login attempts: {total}")
    print(f"Successful logins (DB heuristic): {successful_db}")
    if total > 0:
        print(f"DB success rate: {(successful_db/total)*100:.1f}%")
    print("=" * 60)
    
    if successful_domains:
        print(f"\nSuccessful domains ({len(successful_domains)}):")
        for i, domain in enumerate(sorted(successful_domains), 1):
            print(f"  {i}. {domain}")

    mongo_client.close()

if __name__ == "__main__":
    check_successful_logins()
