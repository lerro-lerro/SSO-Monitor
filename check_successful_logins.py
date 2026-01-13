#!/usr/bin/env python3
"""
Check successful SSO logins in SSO-Monitor database
"""

from pymongo import MongoClient

MONGODB_HOST = "100.96.95.92"
MONGODB_PORT = 27017
DATABASE_NAME = "sso-monitor"
COLLECTION_NAME = "login_trace_analysis_tres"

def check_successful_logins():
    client = MongoClient(MONGODB_HOST, MONGODB_PORT, serverSelectionTimeoutMS=5000)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    
    total = collection.count_documents({})
    successful = collection.count_documents({
        "login_trace_analysis_result.idp_login_request": {"$ne": None},
        "login_trace_analysis_result.idp_login_response": {"$ne": None},
        "$or": [
            # Google One Tap / Modern integrations - success if channelmessage exists with credential
            {
                "login_trace_analysis_result.idp_login_response_channelmessage": {"$ne": None},
                "login_trace_analysis_result.idp_login_response_channelmessage.data.response.credential": {"$ne": None}
            },
            # Traditional OAuth redirects - success if response has code or callback
            {
                "login_trace_analysis_result.idp_login_response": {"$regex": "code=|callback"},
                "login_trace_analysis_result.idp_login_response_channelmessage": None
            },
            # Fallback: if storage state was captured, login succeeded (has auth tokens)
            {
                "login_trace_analysis_result.login_trace_storage_state": {"$ne": None, "$type": "object"}
            }
        ]
    })
    
    print(f"{'='*50}")
    print(f"Total login attempts: {total}")
    print(f"Successful logins (excluding mock domain): {successful}")
    if total > 0:
        print(f"Success rate: {(successful/total)*100:.1f}%")
    print(f"{'='*50}\n")
    
    if successful > 0:
        print("Successful login URLs:\n")
        logins = collection.aggregate([
            {
                "$match": {
                    "login_trace_analysis_result.idp_login_request": {"$ne": None},
                    "login_trace_analysis_result.idp_login_response": {"$ne": None},
                    "$or": [
                        # Google One Tap / Modern integrations - success if credential received
                        {
                            "login_trace_analysis_result.idp_login_response_channelmessage": {"$ne": None},
                            "login_trace_analysis_result.idp_login_response_channelmessage.data.response.credential": {"$ne": None}
                        },
                        # Traditional OAuth redirects - success if response has code or callback
                        {
                            "login_trace_analysis_result.idp_login_response": {"$regex": "code=|callback"},
                            "login_trace_analysis_result.idp_login_response_channelmessage": None
                        },
                        # Fallback: if storage state was captured, login succeeded (has auth tokens)
                        {
                            "login_trace_analysis_result.login_trace_storage_state": {"$ne": None, "$type": "object"}
                        }
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$domain",
                    "domain": {"$first": "$domain"},
                    "config": {"$first": "$login_trace_analysis_config"}
                }
            },
            {
                "$sort": {"domain": 1}
            }
        ])
        
        counter = 0
        
        for login in logins:
            counter += 1
            domain = login.get('domain', 'N/A')
            url = login.get('config', {}).get('login_page_url', 'N/A')
            print(f"{counter}. Domain: {domain}")
            print(f"   URL: {url}\n")
    
    client.close()

if __name__ == "__main__":
    check_successful_logins()