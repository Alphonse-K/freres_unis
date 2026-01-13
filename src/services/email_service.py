# src/services/email_service.py
import logging
from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:

    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str):
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            with SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        except SMTPException as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    @staticmethod
    def send_otp_email(email: str, name: str, otp: str, purpose: str):
        subject = f"Your {purpose.upper()} OTP Code"
        html = f"""
        <p>Hello {name},</p>
        <p>Your OTP code for {purpose} is: <b>{otp}</b></p>
        <p>This code will expire in 5 minutes.</p>
        """
        EmailService.send_email(email, subject, html)

    @staticmethod
    def send_login_notification(email: str, name: str, ip_address: str = ""):
        subject = "New Login Detected"
        html = f"""
        <p>Hello {name},</p>
        <p>A login to your account was detected from IP: {ip_address or 'unknown'}.</p>
        <p>If this wasn’t you, please secure your account immediately.</p>
        """
        EmailService.send_email(email, subject, html)

    @staticmethod
    def send_password_change_notification(to_email: str, name: str, ip: str = ""):
        subject = "Password Changed Successfully"
        html = f"""
        <p>Hello {name},</p>
        <p>Your account password was successfully changed.</p>
        <p>IP address: {ip or "unknown"}</p>
        <p>If you did not perform this action, contact support immediately.</p>
        """
        EmailService.send_email(to_email, subject, html)
