import os
import json
import time
import random
import datetime

# Check if we should use the local emulator fallback
USE_EMULATOR = True
FIREBASE_KEY_PATH = "firebase_key.json"

db = None

if os.path.exists(FIREBASE_KEY_PATH) and os.path.getsize(FIREBASE_KEY_PATH) > 0:
    try:
        with open(FIREBASE_KEY_PATH, "r") as f:
            config = json.load(f)
            if "project_id" in config:
                import firebase_admin
                from firebase_admin import credentials, firestore
                
                # Prevent double-initialization
                if not firebase_admin._apps:
                    cred = credentials.Certificate(FIREBASE_KEY_PATH)
                    firebase_admin.initialize_app(cred)
                db = firestore.client()
                USE_EMULATOR = False
                print("[AUTH] Successfully connected to Firebase Admin SDK and Firestore client.")
    except Exception as e:
        print(f"[AUTH] Warning: Failed to load Firebase certificate: {e}. Falling back to Emulator.")
        USE_EMULATOR = True

# Persistent local emulator DB file
EMULATOR_FILE = "firebase_emulator.json"

def seed_emulator():
    """
    Seeds local database with default users and roles.
    """
    default_db = {
        "users": {
            "officer@agriaudit.gov": {
                "uid": "uid_procurement_officer_901",
                "email": "officer@agriaudit.gov",
                "password": "password123",  # Plain text for demo; in prod this would be hashed
                "role": "Procurement Officer",
                "two_factor_enabled": True,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
                "failed_attempts": 0,
                "lockout_until": 0
            },
            "auditor@agriaudit.gov": {
                "uid": "uid_auditor_402",
                "email": "auditor@agriaudit.gov",
                "password": "password123",
                "role": "Auditor",
                "two_factor_enabled": True,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
                "failed_attempts": 0,
                "lockout_until": 0
            },
            "admin@agriaudit.gov": {
                "uid": "uid_admin_707",
                "email": "admin@agriaudit.gov",
                "password": "password123",
                "role": "Admin",
                "two_factor_enabled": True,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
                "failed_attempts": 0,
                "lockout_until": 0
            }
        },
        "auth_logs": [],
        "otps": {}
    }
    
    if not os.path.exists(EMULATOR_FILE) or os.path.getsize(EMULATOR_FILE) == 0:
        with open(EMULATOR_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=2)

# Ensure emulator has default credentials seeded
if USE_EMULATOR:
    seed_emulator()

def get_emulator_data():
    if not os.path.exists(EMULATOR_FILE):
        seed_emulator()
    try:
        with open(EMULATOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        seed_emulator()
        with open(EMULATOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_emulator_data(data):
    try:
        with open(EMULATOR_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[AUTH] Error saving emulator database: {e}")

# =====================================================================
# CORE AUTHENTICATION OPERATIONS
# =====================================================================

def authenticate_user(email, password):
    """
    Validates user credentials, enforcing account lockouts and rate limiting.
    """
    email = email.strip().lower()
    now_ts = int(time.time())
    
    if USE_EMULATOR:
        data = get_emulator_data()
        users = data.get("users", {})
        
        if email not in users:
            return False, "User not found.", None
            
        user = users[email]
        
        # Check lockout
        lockout_until = user.get("lockout_until", 0)
        if now_ts < lockout_until:
            rem_sec = int(lockout_until - now_ts)
            return False, f"Account temporarily locked. Try again in {rem_sec} seconds.", None
            
        # Verify Password
        if user["password"] == password:
            # Success
            user["failed_attempts"] = 0
            user["lockout_until"] = 0
            save_emulator_data(data)
            return True, "Credentials verified successfully.", {
                "uid": user["uid"],
                "email": user["email"],
                "role": user["role"],
                "two_factor_enabled": user["two_factor_enabled"]
            }
        else:
            # Failed attempt
            attempts = user.get("failed_attempts", 0) + 1
            user["failed_attempts"] = attempts
            
            msg = "Invalid password."
            if attempts >= 3:
                user["lockout_until"] = now_ts + 300  # Lock for 5 minutes (300 seconds)
                msg = "Account locked for 5 minutes due to too many failed login attempts."
            else:
                msg = f"Invalid password. {3 - attempts} attempts remaining."
                
            save_emulator_data(data)
            return False, msg, None
            
    else:
        # If Real Firebase is used, verify via custom collections or local mirroring
        # since Firebase Admin does not directly authenticate passwords (typically client-side).
        # We mirror Firestore config for role authentication
        try:
            user_ref = db.collection("users").document(email)
            doc = user_ref.get()
            
            if not doc.exists:
                # Seed user in Firestore if not exists
                user_ref.set({
                    "uid": f"uid_{email.split('@')[0]}",
                    "email": email,
                    "password": password, # Seed plain for demo matching
                    "role": "Procurement Officer" if "officer" in email else ("Admin" if "admin" in email else "Auditor"),
                    "two_factor_enabled": True,
                    "created_at": datetime.datetime.now().isoformat(),
                    "failed_attempts": 0,
                    "lockout_until": 0
                })
                doc = user_ref.get()
                
            u_data = doc.to_dict()
            
            lockout_until = u_data.get("lockout_until", 0)
            if now_ts < lockout_until:
                rem_sec = int(lockout_until - now_ts)
                return False, f"Account locked. Try again in {rem_sec}s.", None
                
            if u_data.get("password") == password:
                user_ref.update({"failed_attempts": 0, "lockout_until": 0})
                return True, "Credentials verified successfully.", {
                    "uid": u_data["uid"],
                    "email": u_data["email"],
                    "role": u_data["role"],
                    "two_factor_enabled": u_data["two_factor_enabled"]
                }
            else:
                attempts = u_data.get("failed_attempts", 0) + 1
                lockout = now_ts + 300 if attempts >= 3 else 0
                user_ref.update({"failed_attempts": attempts, "lockout_until": lockout})
                
                msg = f"Invalid password. {3 - attempts} attempts remaining." if attempts < 3 else "Account locked for 5 minutes."
                return False, msg, None
        except Exception as e:
            return False, f"Firebase error: {str(e)}", None


def generate_otp(email):
    """
    Generates a 6-digit OTP code, sets expiration, and registers it.
    """
    email = email.strip().lower()
    otp_code = "".join(random.choices("0123456789", k=6))
    expiry = int(time.time()) + 120  # Expires in 2 minutes (120 seconds)
    
    if USE_EMULATOR:
        data = get_emulator_data()
        data["otps"][email] = {
            "code": otp_code,
            "expiry": expiry,
            "used": False
        }
        save_emulator_data(data)
    else:
        try:
            db.collection("otps").document(email).set({
                "code": otp_code,
                "expiry": expiry,
                "used": False
            })
        except Exception as e:
            print(f"[AUTH] Error writing OTP to Firestore: {e}")
            
    # CRITICAL: Print to terminal console for reviewer/demo copying
    print("\n" + "=" * 50)
    print(f"[2FA AUTHENTICATION CODE]")
    print(f"User: {email}")
    print(f"OTP Verification Code: {otp_code}")
    print(f"Expires in: 120 seconds")
    print("=" * 50 + "\n")
    
    return otp_code


def verify_otp(email, code):
    """
    Validates OTP, checking match, expiration, and single-use rules.
    """
    email = email.strip().lower()
    code = code.strip()
    now_ts = int(time.time())
    
    if USE_EMULATOR:
        data = get_emulator_data()
        otp_records = data.get("otps", {})
        
        if email not in otp_records:
            return False, "No code generated for this session.", None
            
        record = otp_records[email]
        
        if record["used"]:
            return False, "This verification code has already been used.", None
            
        if now_ts > record["expiry"]:
            return False, "This verification code has expired. Please request a new one.", None
            
        if record["code"] != code:
            return False, "Invalid verification code.", None
            
        # Mark as used
        record["used"] = True
        
        # Update user last login
        users = data.get("users", {})
        user = users.get(email, {})
        if user:
            user["last_login"] = datetime.datetime.now().isoformat()
            
        save_emulator_data(data)
        
        return True, "Verification successful.", {
            "uid": user.get("uid", "unknown"),
            "email": email,
            "role": user.get("role", "Auditor")
        }
    else:
        try:
            otp_ref = db.collection("otps").document(email)
            doc = otp_ref.get()
            
            if not doc.exists:
                return False, "No code generated.", None
                
            record = doc.to_dict()
            if record.get("used"):
                return False, "Verification code already used.", None
                
            if now_ts > record.get("expiry", 0):
                return False, "Verification code expired.", None
                
            if record.get("code") != code:
                return False, "Invalid code.", None
                
            # Mark as used and update login timestamp
            otp_ref.update({"used": True})
            
            user_ref = db.collection("users").document(email)
            user_doc = user_ref.get()
            user_role = "Auditor"
            user_uid = "unknown"
            
            if user_doc.exists:
                user_role = user_doc.to_dict().get("role", "Auditor")
                user_uid = user_doc.to_dict().get("uid", "unknown")
                user_ref.update({"last_login": datetime.datetime.now().isoformat()})
                
            return True, "Verification successful.", {
                "uid": user_uid,
                "email": email,
                "role": user_role
            }
        except Exception as e:
            return False, f"Firestore verification failed: {str(e)}", None


def log_auth_event(email, success, otp_verified, failed_attempts, ip_address="127.0.0.1", device_info="Web Browser"):
    """
    Appends security logs into Firestore / emulator log collection.
    """
    email = email.strip().lower()
    
    log_entry = {
        "email": email,
        "login_time": datetime.datetime.now().isoformat(),
        "ip_address": ip_address,
        "otp_verified": otp_verified,
        "failed_attempts": failed_attempts,
        "device_info": device_info,
        "status": "SUCCESS" if success else "FAILED"
    }
    
    if USE_EMULATOR:
        data = get_emulator_data()
        data["auth_logs"].append(log_entry)
        save_emulator_data(data)
    else:
        try:
            db.collection("auth_logs").add(log_entry)
        except Exception as e:
            print(f"[AUTH] Error writing auth log: {e}")
