"""Transactional e-mail over an HTTPS API (Render's free tier blocks SMTP ports).

EMAIL_PROVIDER = brevo | resend | smtp     (unset -> nothing is sent; codes go to the server log in dev)
EMAIL_FROM     = a sender address the provider has verified
EMAIL_FROM_NAME= display name (default 'AURA Campus')
BREVO_API_KEY / RESEND_API_KEY             or  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
"""
import asyncio
import json
import logging
import os
import smtplib
import urllib.request
from email.message import EmailMessage

log = logging.getLogger("aura.mail")
UA = "aura-campus/1.0"


def provider() -> str:
    return (os.environ.get("EMAIL_PROVIDER") or "").strip().lower()


def configured() -> bool:
    return provider() in ("brevo", "resend", "smtp") and bool(os.environ.get("EMAIL_FROM"))


def _post_json(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def _send_sync(to: str, subject: str, text: str, html: str = None):
    prov, sender = provider(), os.environ["EMAIL_FROM"]
    name = os.environ.get("EMAIL_FROM_NAME", "AURA Campus")
    if prov == "brevo":
        body = {"sender": {"name": name, "email": sender}, "to": [{"email": to}], "subject": subject, "textContent": text}
        if html:
            body["htmlContent"] = html
        _post_json("https://api.brevo.com/v3/smtp/email", {"api-key": os.environ["BREVO_API_KEY"]}, body)
    elif prov == "resend":
        body = {"from": f"{name} <{sender}>", "to": [to], "subject": subject, "text": text}
        if html:
            body["html"] = html
        _post_json("https://api.resend.com/emails", {"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"}, body)
    elif prov == "smtp":
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = f"{name} <{sender}>", to, subject
        msg.set_content(text)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=20) as s:
            s.starttls()
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            s.send_message(msg)
    else:
        raise RuntimeError("EMAIL_PROVIDER not configured")


async def send_email(to: str, subject: str, text: str, html: str = None) -> bool:
    """True if the provider accepted the message. Never raises."""
    if not configured():
        log.warning("E-mail not configured; would have sent to %s: %s | %s", to, subject, text.replace("\n", " "))
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, text, html)
        return True
    except Exception:                                           # noqa: BLE001
        log.exception("Sending e-mail to %s failed", to)
        return False


def code_message(name: str, code: str, purpose: str):
    what = "verify your email address" if purpose == "verify" else "reset your password"
    subject = f"AURA: your {'verification' if purpose == 'verify' else 'password reset'} code is {code}"
    text = (f"Hi {name},\n\nUse this code to {what}: {code}\n\nIt expires in 15 minutes. "
            f"If you did not ask for it, ignore this email — nothing will change.\n\n— AURA Campus")
    html = (f"<p>Hi {name},</p><p>Use this code to {what}:</p>"
            f"<p style='font-size:28px;letter-spacing:6px;font-weight:700'>{code}</p>"
            f"<p>It expires in 15 minutes. If you did not ask for it, ignore this email.</p>")
    return subject, text, html
