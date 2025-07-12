"""Email sending module using Gmail SMTP."""
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from .settings import settings
from .utils.logger import get_logger

logger = get_logger(__name__)


class Emailer:
    """Handles sending emails via Gmail SMTP."""
    
    def __init__(self):
        """Initialize the emailer."""
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender = settings.gmail_from
        self.recipient = settings.gmail_to
        self.app_password = settings.gmail_app_password
        
    def send_email(
        self,
        subject: str,
        body: str,
        recipient: Optional[str] = None,
        is_html: bool = False,
    ) -> bool:
        """Send an email via Gmail SMTP.
        
        Args:
            subject: Email subject
            body: Email body content
            recipient: Override recipient (defaults to settings.gmail_to)
            is_html: Whether the body is HTML format
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.app_password:
            logger.warning("No Gmail app password configured, skipping email")
            return False
            
        recipient = recipient or self.recipient
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Attach body
            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type))
            
            # Connect to server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.app_password)
                server.send_message(msg)
                
            logger.info(
                "Email sent successfully",
                subject=subject,
                recipient=recipient,
                size=len(body),
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                subject=subject,
                recipient=recipient,
                error=str(e),
            )
            return False
    
    def send_daily_brief(self, content: str, date: Optional[datetime] = None) -> bool:
        """Send the daily briefing email.
        
        Args:
            content: Briefing content
            date: Date for the briefing (defaults to today)
            
        Returns:
            True if sent successfully
        """
        date = date or datetime.now()
        date_str = date.strftime("%B %d, %Y")
        
        subject = f"Jarvis Daily Brief - {date_str}"
        
        return self.send_email(subject, content)
    
    def send_alert_email(
        self,
        missing_fields: List[str],
        date: Optional[datetime] = None,
    ) -> bool:
        """Send an alert email for missing fields.
        
        Args:
            missing_fields: List of field names that are missing
            date: Date of the briefing
            
        Returns:
            True if sent successfully
        """
        if not missing_fields:
            return True
            
        date = date or datetime.now()
        date_str = date.strftime("%B %d, %Y")
        
        subject = f"Jarvis BriefMe - Missing Fields Alert - {date_str}"
        
        # Build the alert body
        body_lines = [
            f"Missing Fields Alert for {date_str}",
            "",
            f"The following {len(missing_fields)} fields could not be populated:",
            "",
        ]
        
        # Add missing fields as a bulleted list
        for field in sorted(missing_fields):
            body_lines.append(f"  • {field}")
            
        body_lines.extend([
            "",
            "The daily briefing was still generated and sent with '(data unavailable)' placeholders for these fields.",
            "",
            "Please check the data sources and API connections.",
        ])
        
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body)
    
    def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None,
    ) -> bool:
        """Send an error notification email.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context information
            
        Returns:
            True if sent successfully
        """
        subject = f"Jarvis BriefMe - Error: {error_type}"
        
        body_lines = [
            f"Error Type: {error_type}",
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "Error Message:",
            error_message,
            "",
        ]
        
        if context:
            body_lines.extend([
                "Context:",
                "",
            ])
            for key, value in context.items():
                body_lines.append(f"  {key}: {value}")
                
        body = "\n".join(body_lines)
        
        return self.send_email(subject, body)
    
    def test_connection(self) -> bool:
        """Test the SMTP connection.
        
        Returns:
            True if connection successful
        """
        if not self.app_password:
            logger.warning("No Gmail app password configured")
            return False
            
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.app_password)
                
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False