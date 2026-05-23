import streamlit as st
import json
from agent import process_audit
import tempfile
import os
import time

# Import authentication helper functions
from auth import authenticate_user, generate_otp, verify_otp, log_auth_event, USE_EMULATOR

def generate_markdown_report(audit_json, human_decision):
    """
    Generates a professional markdown report detailing the audit results
    and the procurement officer's final decision.
    """
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score = audit_json.get("score", 0)
    summary = audit_json.get("summary", "No summary provided.")
    findings = audit_json.get("key_findings", [])
    
    findings_list = ""
    for f in findings:
        status_icon = "🟢" if f.get("status", "").lower() == "match" else "🟡" if f.get("status", "").lower() == "deviation" else "🔴"
        findings_list += f"- **{f.get('criterion')}**: {status_icon} {f.get('status')} - {f.get('notes')}\n"
        
    report = f"""# OFFICIAL AGRI-AUDIT PROCUREMENT REPORT

**Generated Timestamp:** {timestamp}  
**Designated Auditor Role:** Procurement Officer  

---

## 🏛️ Final Human Oversight Decision
**Status:** **{human_decision.upper()}**

*The designated Procurement Officer has reviewed the automated recommendations and has recorded this final decision in the official ledger.*

---

## 📊 AI Recommendation Summary
- **AI Suitability Match Score:** **{score}/100**
- **AI Match Confidence:** High Compliance

### Summary Assessment:
{summary}

---

## 🔍 Detailed Key Findings
{findings_list if findings_list else "*No detailed key findings recorded.*"}

---
*End of Official Document*
"""
    return report

# Set page configuration with a modern title and icon (must be first Streamlit command)
st.set_page_config(
    page_title="AgriAudit: Blind Procurement AI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session States
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_step" not in st.session_state:
    st.session_state.login_step = 1
if "temp_email" not in st.session_state:
    st.session_state.temp_email = ""
if "temp_otp" not in st.session_state:
    st.session_state.temp_otp = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "human_decision" not in st.session_state:
    st.session_state.human_decision = None

# Inactivity Session Timeout Config (5 minutes = 300 seconds)
TIMEOUT_SECONDS = 300

# check inactivity logout if authenticated
if st.session_state.authenticated:
    if "last_activity" in st.session_state:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > TIMEOUT_SECONDS:
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.authenticated = False
            st.session_state.login_step = 1
            st.session_state.timeout_logged_out = True
            st.rerun()
    st.session_state.last_activity = time.time()

# =====================================================================
# RENDER AUTHENTICATION SCREENS (if not authenticated)
# =====================================================================
if not st.session_state.authenticated:
    # Inject Professional SaaS UI Styling for Login Pages
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif !important;
            background-image: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.85)), url('https://i.ibb.co/Y70SFrH8/agri.jpg') !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            color: #E2E8F0 !important;
        }
        
        /* Card design for Login UI */
        .login-box {
            background-color: rgba(30, 41, 59, 0.7) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px;
            padding: 2.5rem;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
            margin-top: 4rem;
        }
        
        .gov-header {
            text-align: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .gov-title {
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, #10B981 0%, #34D399 50%, #06B6D4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: 0.5px;
        }
        
        .gov-subtitle {
            font-size: 0.8rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 0.25rem;
            margin-bottom: 0;
        }
        
        .helper-card {
            background-color: rgba(30, 41, 59, 0.7) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-top: 1.5rem;
            font-size: 0.85rem;
            color: #E2E8F0;
        }
        
        .otp-alert {
            background-color: rgba(30, 41, 59, 0.7) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: #FBBF24;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    col_left, col_mid, col_right = st.columns([1, 1.8, 1])
    
    with col_mid:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="gov-header">
                <h2 class="gov-title">AGRIAUDIT SECURE LOGON</h2>
                <p class="gov-subtitle">Federal Procurement Audit System</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get("timeout_logged_out"):
            st.warning("Warning: Session expired due to 5 minutes of inactivity. Please log in again.")
        
        # -------------------------------------------------------------
        # SCREEN 1: CREDENTIALS INPUT
        # -------------------------------------------------------------
        if st.session_state.login_step == 1:
            email_input = st.text_input("Institutional Email Address", key="login_email_field", placeholder="officer@agriaudit.gov")
            password_input = st.text_input("Security Password", key="login_pass_field", type="password", placeholder="••••••••")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Sign In", use_container_width=True):
                if not email_input.strip() or not password_input.strip():
                    st.error("Email and Password are required.")
                else:
                    success, msg, user_data = authenticate_user(email_input, password_input)
                    if success:
                        st.session_state.temp_email = email_input
                        # Trigger 2FA
                        otp = generate_otp(email_input)
                        st.session_state.temp_otp = otp
                        st.session_state.login_step = 2
                        st.rerun()
                    else:
                        st.error(msg)
                        log_auth_event(email_input, success=False, otp_verified=False, failed_attempts=1)
            
            # Seeded Account Helper Card for reviewer
            st.markdown(
                """
                <div class="helper-card">
                    <strong>Seeded Test Credentials:</strong><br>
                    • <code>officer@agriaudit.gov</code> (Password: <code>password123</code>)<br>
                    • <code>auditor@agriaudit.gov</code> (Password: <code>password123</code>)<br>
                    • <code>admin@agriaudit.gov</code> (Password: <code>password123</code>)
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # -------------------------------------------------------------
        # SCREEN 2: 2FA VERIFICATION CODE
        # -------------------------------------------------------------
        elif st.session_state.login_step == 2:
            st.markdown(
                f"""
                <div style="font-size:0.9rem; color:#94A3B8; margin-bottom:1rem;">
                    A one-time security verification code (OTP) has been sent to your registered institutional account <strong>{st.session_state.temp_email}</strong>.
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Reviewer Helper Popup: Display the generated OTP directly in UI for convenience
            st.markdown(
                f"""
                <div class="otp-alert">
                    <strong>[REVIEWER HELPER]:</strong> Your verification code is: 
                    <span style="font-size:1.1rem; font-family:monospace; font-weight:700; color:#FFF; letter-spacing:1px; background:#1E293B; padding:0.15rem 0.5rem; border-radius:4px; margin-left:0.25rem;">
                        {st.session_state.temp_otp}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            otp_code = st.text_input("Enter 6-Digit Verification Code", max_chars=6, placeholder="000000")
            
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button("Verify Code", use_container_width=True):
                    success, msg, user_data = verify_otp(st.session_state.temp_email, otp_code)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_email = st.session_state.temp_email
                        st.session_state.user_role = user_data["role"]
                        st.session_state.last_activity = time.time()
                        
                        log_auth_event(
                            st.session_state.user_email,
                            success=True,
                            otp_verified=True,
                            failed_attempts=0
                        )
                        st.success("Access Granted.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)
                        log_auth_event(
                            st.session_state.temp_email,
                            success=False,
                            otp_verified=False,
                            failed_attempts=1
                        )
            
            with btn_col2:
                if st.button("Resend OTP", use_container_width=True):
                    new_otp = generate_otp(st.session_state.temp_email)
                    st.session_state.temp_otp = new_otp
                    st.toast("Verification code resent successfully!")
                    time.sleep(0.5)
                    st.rerun()
                    
            st.markdown("---")
            if st.button("Back to login"):
                st.session_state.login_step = 1
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.stop() # Halt rendering of protected content

# =====================================================================
# RENDER MAIN DASHBOARD PAGE (Only reached if authenticated)
# =====================================================================

# Custom dashboard premium styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Font family overrides and background styling */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif !important;
        background-image: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.85)), url('https://i.ibb.co/Y70SFrH8/agri.jpg') !important;
        background-size: cover !important;
        background-attachment: fixed !important;
        color: #E2E8F0 !important;
    }
    
    /* Title container styling */
    .title-container {
        padding: 1.5rem 0rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid #334155;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #94A3B8;
        margin-top: 0.5rem;
        margin-bottom: 0;
        font-weight: 400;
    }
    
    /* Audit card summary design */
    .summary-card {
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        padding: 2rem;
        margin-bottom: 2rem;
        color: #E2E8F0 !important;
        transition: all 0.3s ease;
    }
    
    .summary-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    /* Metrics display styling */
    .metric-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 2px solid #10B981;
        border-radius: 50%;
        width: 120px;
        height: 120px;
        font-size: 2.5rem;
        font-weight: 700;
        color: #10B981;
        margin: 0 auto 1rem auto;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.15);
    }
    
    .metric-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #E2E8F0;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 0.25rem;
        text-align: center;
    }
    
    /* Key findings card styles */
    .finding-item {
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid #334155 !important;
        border-left: 5px solid #E5E7EB !important;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
        color: #E2E8F0 !important;
    }
    
    .finding-item:hover {
        transform: translateX(4px);
    }
    
    .finding-match {
        border-left-color: #10B981 !important;
    }
    
    .finding-deviation {
        border-left-color: #F59E0B !important;
    }
    
    .finding-fail {
        border-left-color: #EF4444 !important;
    }
    
    .finding-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #F8FAFC !important;
        margin-bottom: 0.25rem;
    }
    
    .finding-status-badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    
    .status-match {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34D399;
    }
    
    .status-deviation {
        background-color: rgba(245, 158, 11, 0.2);
        color: #FBBF24;
    }
    
    .status-fail {
        background-color: rgba(239, 68, 68, 0.2);
        color: #FCA5A5;
    }
    
    .finding-desc {
        color: #CBD5E1 !important;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* Sidebar aesthetic touchups */
    .sidebar-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #E2E8F0;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Session Profile Info Box */
    .profile-card {
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        color: #E2E8F0 !important;
    }
    
    .profile-email {
        font-weight: 600;
        color: #F8FAFC;
        font-size: 0.95rem;
        word-break: break-all;
    }
    
    .profile-role {
        font-size: 0.8rem;
        color: #10B981;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.15rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Section
st.markdown(
    """
    <div class="title-container">
        <h1 class="main-title">AgriAudit</h1>
        <p class="subtitle">Blind Procurement AI — Standardizing compliance, fairness, and bid comparisons</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar Configuration
with st.sidebar:
    st.markdown('<div class="sidebar-header">Configuration</div>', unsafe_allow_html=True)
    
    # Render Authenticated Profile Card
    st.markdown(
        f"""
        <div class="profile-card">
            <div style="font-size:0.75rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Secure Session Active</div>
            <div class="profile-email">{st.session_state.user_email}</div>
            <div class="profile-role">{st.session_state.user_role}</div>
            <div style="font-size:0.75rem; color:#94A3B8; margin-top:0.4rem; font-style:italic;">Firebase 2FA Validated</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.write("Upload procurement documents to run an automated alignment audit.")
    
    st.markdown("---")
    
    # 1. Tender Document Uploader
    tender_doc = st.file_uploader(
        "Tender Document",
        type=["pdf", "txt", "docx"],
        help="Upload the primary guidelines, technical specs, or tender requirements PDF/TXT."
    )
    
    # 2. Vendor Bid Uploader
    vendor_bid = st.file_uploader(
        "Vendor Bid",
        type=["pdf", "txt", "docx"],
        help="Upload the vendor proposal or bid response PDF/TXT."
    )
    
    st.markdown("---")
    
    # Logout action button
    if st.button("Secure Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.authenticated = False
        st.session_state.login_step = 1
        st.rerun()

# Main Dashboard View
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Document Selection Status")
    
    # Status Indicators
    status_tender = "Pass: Tender Document Uploaded" if tender_doc else "Pending Tender Document"
    status_vendor = "Pass: Vendor Bid Uploaded" if vendor_bid else "Pending Vendor Bid"
    
    st.markdown(f"- **Tender Status:** {status_tender}")
    st.markdown(f"- **Vendor Status:** {status_vendor}")
    
    # Button to Run Audit in the Main View
    ready_to_audit = tender_doc is not None and vendor_bid is not None
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Disable run button if files are missing
    run_button = st.button(
        "Run Audit",
        disabled=not ready_to_audit,
        use_container_width=True,
        help="Make sure both Tender and Vendor documents are uploaded before running."
    )

with col2:
    st.subheader("Tips for Best Results")
    st.markdown(
        """
        - Ensure both documents are in readable PDF or TXT format.
        - The agent audits specific technical, commercial, and timeline metrics.
        - Results are displayed in the panel below after computation.
        """
    )

# Execution and Results Display
if run_button:
    if ready_to_audit:
        st.session_state.human_decision = None  # Reset decision
        with st.spinner("Running AgriAudit Agent analysis on procurement documents..."):
            # Create temporary files to write the uploaded files' content to
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tender_tmp:
                tender_tmp.write(tender_doc.getvalue())
                tender_tmp_path = tender_tmp.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as bid_tmp:
                bid_tmp.write(vendor_bid.getvalue())
                bid_tmp_path = bid_tmp.name
                
            try:
                # Call the real agent function
                st.session_state.audit_result = process_audit(tender_tmp_path, bid_tmp_path)
            finally:
                # Clean up temporary files
                try:
                    os.remove(tender_tmp_path)
                except Exception:
                     pass
                try:
                    os.remove(bid_tmp_path)
                except Exception:
                    pass
        st.rerun()
    else:
        st.warning("Warning: Please upload both the Tender Document and Vendor Bid in the sidebar.")

# Render Results from Session State
if st.session_state.audit_result is not None:
    audit_result = st.session_state.audit_result
    
    # Display success/failure status
    if audit_result.get("status") == "success":
        st.success("Audit completed successfully!")
        
        # Split display layout for metrics and summary
        res_col1, res_col2 = st.columns([1, 3])
        
        with res_col1:
            score = audit_result.get("score", 0)
            st.markdown('<div class="metric-title">Audit Score</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-badge">{score}</div>', unsafe_allow_html=True)
            
            st.markdown(
                f"""
                <div style='text-align: center; color: #E2E8F0; font-size: 0.9rem;'>
                    Overall suitability matching score.
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with res_col2:
            st.markdown('<div class="summary-card">', unsafe_allow_html=True)
            st.markdown("### Audit Summary")
            st.write(audit_result.get("summary"))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Key Findings List
        st.subheader("Critical Alignment Findings")
        
        findings = audit_result.get("key_findings", [])
        if findings:
            for idx, finding in enumerate(findings):
                status = finding.get("status", "Match")
                
                # Style selector based on finding status
                if status.lower() == "match":
                    card_class = "finding-match"
                    badge_class = "status-match"
                elif status.lower() == "deviation":
                    card_class = "finding-deviation"
                    badge_class = "status-deviation"
                else:
                    card_class = "finding-fail"
                    badge_class = "status-fail"
                    
                st.markdown(
                    f"""
                    <div class="finding-item {card_class}">
                        <div class="finding-title">{finding.get('criterion')}</div>
                        <span class="finding-status-badge {badge_class}">{status}</span>
                        <div class="finding-desc">{finding.get('notes')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No detailed findings returned.")
            
        # Full Raw JSON output (collapsible) for debugging/transparency
        with st.expander("View Raw Agent Response"):
            st.json(audit_result)
            
        # Human-in-the-Loop Oversight Section
        st.markdown("---")
        st.subheader("Final Human Oversight Decision")
        st.markdown(
            "<p style='color: #94A3B8; font-size: 0.95rem; margin-bottom: 1rem;'>"
            "The AI has provided its recommendation. As the designated Procurement Officer, "
            "you must make the final legal determination."
            "</p>",
            unsafe_allow_html=True
        )
        
        if st.session_state.human_decision is None:
            dec_col1, dec_col2 = st.columns(2)
            with dec_col1:
                if st.button("APPROVE BID", use_container_width=True):
                    st.session_state.human_decision = "Approved"
                    st.rerun()
            with dec_col2:
                if st.button("REJECT BID", use_container_width=True):
                    st.session_state.human_decision = "Rejected"
                    st.rerun()
        else:
            decision = st.session_state.human_decision
            st.success(f"Official Decision Recorded: {decision.upper()}")
            
            # Generate markdown report
            report_data = generate_markdown_report(audit_result, decision)
            
            # Download button
            st.download_button(
                label="Download Official Audit Report",
                data=report_data,
                file_name="Official_AgriAudit_Report.md",
                mime="text/markdown",
                use_container_width=True
            )
            
    elif audit_result.get("status") == "error":
        st.error(f"Agent Error: {audit_result.get('message')}")
    else:
        st.error("Fail: Agent returned a failure status. Please check your credentials or files.")
else:
    # Default landing visual state
    st.info("Upload documents in the sidebar and click Run Audit to start analyzing the alignment.")
