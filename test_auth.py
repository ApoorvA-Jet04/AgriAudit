import time
import os
import json
from auth import (
    authenticate_user, 
    generate_otp, 
    verify_otp, 
    log_auth_event, 
    get_emulator_data, 
    seed_emulator, 
    EMULATOR_FILE
)

def run_tests():
    print("[*] Initializing Auth Test Suite...")
    
    # 1. Reset/Seed Emulator DB
    if os.path.exists(EMULATOR_FILE):
        os.remove(EMULATOR_FILE)
    seed_emulator()
    
    # 2. Test Correct Credentials Authentication
    print("\n--- TEST 1: Authenticating correct credentials ---")
    success, msg, user = authenticate_user("officer@agriaudit.gov", "password123")
    print(f"Result: success={success}, msg='{msg}'")
    assert success == True
    assert user["role"] == "Procurement Officer"
    print("[PASS] Correct credentials authenticated successfully.")
    
    # 3. Test OTP Generation
    print("\n--- TEST 2: Generating OTP code ---")
    otp = generate_otp("officer@agriaudit.gov")
    print(f"Result: Generated OTP Code = {otp}")
    assert len(otp) == 6
    print("[PASS] OTP generated successfully.")
    
    # 4. Test OTP Verification
    print("\n--- TEST 3: Verifying correct OTP ---")
    success, msg, user = verify_otp("officer@agriaudit.gov", otp)
    print(f"Result: success={success}, msg='{msg}'")
    assert success == True
    assert user["role"] == "Procurement Officer"
    print("[PASS] OTP verified successfully.")
    
    # 5. Test OTP Reuse Prevention
    print("\n--- TEST 4: Verifying OTP reuse prevention ---")
    success, msg, user = verify_otp("officer@agriaudit.gov", otp)
    print(f"Result: success={success}, msg='{msg}'")
    assert success == False
    print("[PASS] OTP reuse correctly blocked.")
    
    # 6. Test Failed Credentials and Lockout Rate Limiting
    print("\n--- TEST 5: testing account lockout rate-limiting ---")
    # Reset emulator to clean attempts
    if os.path.exists(EMULATOR_FILE):
        os.remove(EMULATOR_FILE)
    seed_emulator()
    
    print("Attempt 1 (Wrong password):")
    success, msg, user = authenticate_user("officer@agriaudit.gov", "wrong_password")
    print(f"Result: success={success}, msg='{msg}'")
    
    print("Attempt 2 (Wrong password):")
    success, msg, user = authenticate_user("officer@agriaudit.gov", "wrong_password")
    print(f"Result: success={success}, msg='{msg}'")
    
    print("Attempt 3 (Wrong password - lockout threshold):")
    success, msg, user = authenticate_user("officer@agriaudit.gov", "wrong_password")
    print(f"Result: success={success}, msg='{msg}'")
    assert success == False
    assert "locked" in msg.lower()
    
    print("Attempt 4 (Checking if locked account is blocked immediately):")
    success, msg, user = authenticate_user("officer@agriaudit.gov", "password123")
    print(f"Result: success={success}, msg='{msg}'")
    assert success == False
    assert "locked" in msg.lower()
    print("[PASS] Account lockout correctly enforced after 3 failures.")
    
    # 7. Test Security Logging
    print("\n--- TEST 6: Verifying auth logs storage ---")
    log_auth_event("officer@agriaudit.gov", success=True, otp_verified=True, failed_attempts=0)
    data = get_emulator_data()
    logs = data.get("auth_logs", [])
    print(f"Total log events recorded: {len(logs)}")
    assert len(logs) > 0
    print("Latest log entry details:")
    print(json.dumps(logs[-1], indent=2))
    print("[PASS] Security event logs verified.")
    
    print("\n[+] ALL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
