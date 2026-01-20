from fastapi import APIRouter
from app.database import supabase
from app.models import SuccessResponse, ErrorResponse
from app.dependencies import get_password_hash
from datetime import datetime

router = APIRouter(tags=["system"])

@router.post("/init", response_model=SuccessResponse)
async def init_system():
    # Check if admin user exists
    try:
        response = supabase.table("users").select("*").eq("email", "admin@mentobai.com").execute()
        
        if response.data:
            admin_user = response.data[0]
            return SuccessResponse(data={
                "message": "Admin user already exists",
                "user": {
                    "id": admin_user["id"],
                    "username": admin_user["username"],
                    "email": admin_user["email"]
                }
            })
        
        # Create admin user
        hashed_pw = get_password_hash("Admin123!")
        new_user = {
            "email": "admin@mentobai.com",
            "password": hashed_pw,
            "username": "admin",
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        insert_response = supabase.table("users").insert(new_user).execute()
        
        if insert_response.data:
            created_user = insert_response.data[0]
            return SuccessResponse(data={
                "message": "Admin user created successfully",
                "user": {
                    "id": created_user["id"],
                    "username": created_user["username"],
                    "email": created_user["email"]
                },
                "credentials": {
                    "email": "admin@mentobai.com",
                    "password": "Admin123!"
                }
            })
        else:
             return ErrorResponse(success=False, error={"code": "DB_ERROR", "message": "Failed to create admin user"})
            
    except Exception as e:
        return ErrorResponse(success=False, error={"code": "DB_ERROR", "message": str(e)})
