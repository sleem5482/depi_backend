import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# ── Email configuration (loaded from .env) ────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")           # your Gmail / SMTP address
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")   # app password
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _build_reset_email_html(reset_link: str, user_email: str = "", expires_minutes: int = 30) -> str:
    """Return a styled HTML email body for password reset."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Reset Your Password</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #f0f4f8;
      font-family: 'Segoe UI', Arial, sans-serif;
      color: #334155;
    }}
    .wrapper {{
      max-width: 560px;
      margin: 40px auto;
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    .header {{
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      padding: 40px 32px;
      text-align: center;
    }}
    .header h1 {{
      color: #ffffff;
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .header p {{
      color: rgba(255,255,255,0.85);
      margin-top: 8px;
      font-size: 14px;
    }}
    .body {{
      padding: 36px 32px;
    }}
    .body p {{
      font-size: 15px;
      line-height: 1.7;
      color: #475569;
      margin-bottom: 16px;
    }}
    .btn-container {{
      text-align: center;
      margin: 28px 0;
    }}
    .btn {{
      display: inline-block;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      color: #ffffff !important;
      text-decoration: none;
      padding: 14px 36px;
      border-radius: 50px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      box-shadow: 0 4px 14px rgba(99,102,241,0.4);
    }}
    .divider {{
      border: none;
      border-top: 1px solid #e2e8f0;
      margin: 24px 0;
    }}
    .link-fallback {{
      background: #f8fafc;
      border-radius: 8px;
      padding: 12px 16px;
      word-break: break-all;
      font-size: 13px;
      color: #6366f1;
    }}
    .footer {{
      background: #f8fafc;
      padding: 20px 32px;
      text-align: center;
    }}
    .footer p {{
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.6;
    }}
    .warning {{
      display: flex;
      align-items: flex-start;
      gap: 10px;
      background: #fff7ed;
      border: 1px solid #fed7aa;
      border-radius: 8px;
      padding: 12px 16px;
      margin-top: 16px;
    }}
    .warning span {{
      font-size: 14px;
      color: #92400e;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <!-- Header -->
    <div class="header">
      <h1>🔐 Password Reset</h1>
      <p>DEPI Auth — Account Security</p>
    </div>

    <!-- Body -->
    <div class="body">
      <p>Hi there,</p>
      <p>
        We received a request to reset the password for the account associated with
        <strong>{user_email}</strong>.
        Click the button below to choose a new password:
      </p>

      <div class="btn-container">
        <a href="{reset_link}" class="btn">Reset My Password</a>
      </div>

      <div class="warning">
        <span>
          ⏱️ This link will expire in <strong>{expires_minutes} minutes</strong>.
          If you did not request a password reset, you can safely ignore this email —
          your password will remain unchanged.
        </span>
      </div>

      <hr class="divider"/>

      <p style="font-size:13px; color:#64748b;">
        If the button above doesn't work, copy and paste the link below into your browser:
      </p>
      <div class="link-fallback">{reset_link}</div>
    </div>

    <!-- Footer -->
    <div class="footer">
      <p>
        This email was sent by DEPI Auth system.<br/>
        If you have any questions, please contact our support team.
      </p>
    </div>
  </div>
</body>
</html>
"""


def send_reset_password_email(to_email: str, reset_token: str, expires_minutes: int = 30) -> None:
    """
    Send a password-reset email containing a clickable reset link.
    The email body shows the recipient's email address so they know which account it applies to.

    The reset link points to:
        FRONTEND_URL/reset-password?token=<token>

    Make sure SMTP_USER and SMTP_PASSWORD are set in your .env file.

    Raises:
        Exception: if the email fails to send (caller should handle / log this).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be configured in .env to send emails."
        )

    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    # ── Build MIME message ────────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔐 Reset Your DEPI Password"
    msg["From"] = f"DEPI Auth <{SMTP_USER}>"
    msg["To"] = to_email

    # Plain-text fallback
    plain_text = (
        f"Reset your password by visiting the link below:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {expires_minutes} minutes.\n\n"
        f"If you did not request this, ignore this email."
    )
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(_build_reset_email_html(reset_link, to_email, expires_minutes), "html"))

    # ── Send via SMTP (TLS) ───────────────────────────────────────────────────
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
