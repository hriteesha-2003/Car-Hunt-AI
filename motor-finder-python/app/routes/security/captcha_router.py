from fastapi import APIRouter, HTTPException, Request
from app.models.security.captcha import CaptchaVerifyRequest
from app.utilities.security import generate_captcha_text, generate_captcha_token,verify_captcha_token

captcha_router = APIRouter(prefix="/security", tags=["Security"])

@captcha_router.get("/generate-captcha-token")
async def get_captcha_token(request: Request):
    try:
        client_ip = request.client.host
        captcha_text = generate_captcha_text()
        token = generate_captcha_token(client_ip,captcha_text)
        return {
            "captcha_text": captcha_text, #remove in production
            "captcha_token": token
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@captcha_router.post("/verify-captcha")
def verify_captcha(data: CaptchaVerifyRequest, request: Request):
    try:
        ip = request.client.host
        if not verify_captcha_token(data.token, data.captcha_text, ip):
            raise HTTPException(status_code=400, detail="Invalid or expired CAPTCHA.")
        return {"message": "CAPTCHA verified successfully."}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
