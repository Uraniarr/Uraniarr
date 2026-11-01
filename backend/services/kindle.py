import smtplib
from email.message import EmailMessage
from pathlib import Path

from backend.config import ConfigManager
from backend.dependencies import get_logger
from backend.exceptions import KindleError

def send_to_kindle(file: str | Path, kindle_idx: int, cfg: ConfigManager):
    kindle_cfg = cfg.sendtokindle
    recipients = [email.strip() for email in kindle_cfg["kindle_emails"].split(",") if email.strip()]
    if not recipients:
        raise ValueError("No Kindle email addresses configured")

    if kindle_idx >= 0:
        if kindle_idx >= len(recipients):
            get_logger().error("Invalid kindle_idx selected. Out of bounds. Using first configured")
            kindle_idx = 0
        recipients = [recipients[kindle_idx]]

    file = Path(file)

    email = kindle_cfg.get("email_address")
    smtp_port = kindle_cfg.get("smtp_port")
    smtp_server = kindle_cfg.get("smtp_server")
    pw = kindle_cfg.get("password")

    if not (email and smtp_port and smtp_server and pw):
        raise ValueError("sendtokindle config mal-formed")

    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = "Send to Kindle"
    msg.set_content("")

    msg.add_attachment(
        file.read_bytes(),
        maintype="application",
        subtype="epub+zip",
        filename=file.name
    )

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
        smtp.login(email, pw)
        smtp.send_message(msg, to_addrs=recipients)