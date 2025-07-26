import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from fastapi import HTTPException
from config  import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
from .email_template_service import EmailTemplateService  # This is now Mongo-based

class EmailService:
    def __init__(self, db):
        """
        `db` is a PyMongo database instance (e.g., client["your_db"])
        """
        self.db = db
        self.template_service = EmailTemplateService(db)
    
    def send_email(self, template_type: str, to_email: str, **template_vars):
        """Generic email sending method"""
        if not SENDGRID_FROM_EMAIL:
            raise HTTPException(status_code=500, detail="Sender email is not configured.")
        
        subject, html_content = self.template_service.render_template(
            template_type, 
            **template_vars
        )
        
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        # print("message",message)
        
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            print(f"Email sent to {to_email}: {response.status_code}")
            print("Response headers:", response.headers)
            print("Message ID:", response.headers.get("X-Message-Id", "Not available"))
            
            if response.status_code != 202:
                raise HTTPException(status_code=500, detail="SendGrid API did not accept the email.")
                
        except Exception as e:
            print(f"SendGrid error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send email")
    
    def send_password_email(self, to_email: str, password: str,username: str):
        """Send password email using template"""
        print(to_email, password)
        return self.send_email(
            template_type="password",
            to_email=to_email,
            password=password,
            username=username
        )
    
    def send_otp_email(self, to_email: str, otp: str, expiry_minutes: int = 5):
        """Send OTP email using template"""
        return self.send_email(
            template_type="otp",
            to_email=to_email,
            otp=otp,
            expiry_minutes=expiry_minutes
        )
    
    def send_welcome_email(self, to_email: str, username: str):
        """Send welcome email using template"""
        return self.send_email(
            template_type="welcome",
            to_email=to_email,
            username=username,
            
        )
