from fastapi import HTTPException
import re
from bson.objectid import ObjectId

class EmailTemplateService:
    def __init__(self, db):
        """
        `db` should be the pymongo database instance, e.g., client["your_db_name"]
        Access the email_templates collection with: db["email_templates"]
        """
        self.collection = db["email_templates"]
    
    def get_template(self, template_type: str) -> dict:
        """Fetch email template by type"""
        template = self.collection.find_one({
            "template_type": template_type,
            "is_active": True
        })

        if not template:
            raise HTTPException(
                status_code=404, 
                detail=f"Email template '{template_type}' not found"
            )
        
        return template
    
    def render_template(self, template_type: str, **kwargs) -> tuple[str, str]:
        """Render template with dynamic variables"""
        template = self.get_template(template_type)

        print("template",template)
        
        subject = self._replace_placeholders(template.get("subject", ""), **kwargs)
        html_content = self._replace_placeholders(template.get("html_content", ""), **kwargs)
        
        return subject, html_content
    
    def _replace_placeholders(self, content: str, **kwargs) -> str:
        """Replace {{variable}} placeholders with actual values"""
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        
        # # Warn if any unreplaced placeholders remain
        # unreplaced = re.findall(r'\{\{(\w+)\}\}', content)
        # if unreplaced:
        #     print(f"Warning: Unreplaced placeholders found: {unreplaced}")
        
        return content
