import smtplib
from email.message import EmailMessage
from pathlib import Path

from backend.config import ConfigManager
from backend.dependencies import get_logger
from backend.exceptions import KindleError

def send_to_kindle(file: str | Path, kindle_idx: int, cfg: ConfigManager):
    recipients = [email.strip() for email in cfg.kindle_emails.split(",") if email.strip()]
    if not recipients:
        raise ValueError("No Kindle email addresses configured")

    if kindle_idx >= 0:
        if kindle_idx >= len(recipients):
            get_logger().error("Invalid kindle_idx selected. Out of bounds. Using first configured")
            kindle_idx = 0
        recipients = [recipients[kindle_idx]]

    file = Path(file)

    msg = EmailMessage()
    msg["From"] = cfg.email_address
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = "Send to Kindle"
    msg.set_content("")

    msg.add_attachment(
        file.read_bytes(),
        maintype="application",
        subtype="epub+zip",
        filename=file.name
    )

    with smtplib.SMTP_SSL(cfg.smtp_server, cfg.smtp_port) as smtp:
        smtp.login(cfg.email_address, cfg.password)
        smtp.send_message(msg, to_addrs=recipients)