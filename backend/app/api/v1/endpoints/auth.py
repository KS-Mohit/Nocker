from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.browser.linkedin_auth import LinkedInAuth

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login_to_linkedin(request: LoginRequest):
    """
    Login to LinkedIn and save session cookies
    """
    auth = LinkedInAuth()
    
    try:
        success = await auth.login(request.email, request.password)
        
        if success:
            return {
                "success": True,
                "message": "Successfully logged in to LinkedIn. Cookies saved."
            }
        else:
            raise HTTPException(status_code=401, detail="Login failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-login")
async def check_login_status():
    """
    Check if LinkedIn session is still valid
    """
    auth = LinkedInAuth()
    
    try:
        is_logged_in = await auth.is_logged_in()
        
        return {
            "logged_in": is_logged_in,
            "message": "Session active" if is_logged_in else "Please login"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))