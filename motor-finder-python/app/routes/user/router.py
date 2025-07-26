from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from app.database.db import db, user_collection
from app.models.user.user import Role, User, UserLogin,ForgotPasswordRequest,reset_password
from app.utilities.security import create_access_token, hash_password, verify_password,generate_random_password
from app.utilities.security import get_current_user
from app.services.email_service import EmailService
from bson import ObjectId
import random,string
import traceback



auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# Create a new user
@auth_router.post("/create-user")
async def create_user(data: User):
    try:
        if user_collection.find_one({"username": data.username}):
            raise HTTPException(status_code=400, detail="username already registered")

        is_superuser = data.role in [Role.SUPERUSER, Role.ADMIN]
        user_collection.insert_one({
            "role": data.role,
            "username": data.username,
            "email": data.email,
            "password": hash_password(data.password),
            "is_superuser": is_superuser,
            "created_at": datetime.now(timezone.utc)
        })

        return JSONResponse(status_code=201, content={"message": "User created successfully"})

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get user profile
@auth_router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Welcome {current_user['username']}",
        "username": current_user["username"],
        "email": current_user["email"],
        "role": current_user["role"]
    }

# User login
@auth_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    #print(form_data)
    try:
        user = user_collection.find_one({"username": form_data.username})
        if not user:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        if not verify_password(form_data.password, user["password"]):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        role = user.get("role", "unknown")
        is_superuser = user.get("is_superuser", False)

        if role not in ["superuser","admin","user", "freelancer", "buyer", "agent", "client"]:
            raise HTTPException(status_code=403, detail="Unauthorized role")

        access_token = create_access_token(
            data={"sub": str(user["_id"]), "role": role}
        )

        return JSONResponse(
            status_code=200,
            content={
                "access_token": access_token,
                "token_type": "bearer",
                "message": f"{role.capitalize()} login successful",
                "user": {
                    "role": role,
                    "username": user["username"],
                    "email": user["email"],
                    "is_superuser": is_superuser,
                },
            },
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Forget password
@auth_router.post("/forget-password")
async def forget_password(request: ForgotPasswordRequest):
    try:
        print("🔍 Username received:", request.username)
        user = user_collection.find_one({"username": request.username})
        

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        to_email = user.get("email")
        if not to_email: 
                raise HTTPException(status_code=500, detail="Email not found for user")

        username = user.get("username")
        new_password = generate_random_password()
        hashed_password = hash_password(new_password)

        user_collection.update_one(
            {"username": request.username},
            {"$set": {"password": hashed_password}}
        )
        print("🔑 New password:", new_password)
        print("✅ Email about to be sent to:", user["email"])
        # await send_email(
        #     to_email=user["email"],
        #     subject="Your New Password",
        #     content=(
        #         f"Hello {user['username']},\n\n"
        #         f"Your new password is: {new_password}\n\n"
        #         f"Please log in and change it as soon as possible."
        #     )
        # )
        print(username)

        # print(db)

        email_service = EmailService(db)
        email_service.send_password_email(
        to_email=user["email"],
        password=new_password,
        username=username
    )
        return {"message": "New password has been sent to your registered email."}

    except Exception as e:
   
       traceback.print_exc()
       print("Forget password error:", repr(e))
       raise HTTPException(status_code=500, detail="Random password generation failed")

@auth_router.post("/reset-password")
async def reset_password(request: reset_password):
    try:
        user = user_collection.find_one({"username": request.username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(request.temporary_password, user["password"]):
            raise HTTPException(status_code=400, detail="Temporary password is incorrect")

        hashed_new_password = hash_password(request.new_password)
        user_collection.update_one(
            {"username": request.username},
            {"$set": {"password": hashed_new_password}}
        )

        return {"message": "Password has been successfully reset"}

    except Exception as e:
       traceback.print_exc()  # 👈 shows full error in terminal
    print("Reset password error:", repr(e))  # 👈 prints the actual Python error
    raise HTTPException(status_code=500, detail="Internal Server Error")


