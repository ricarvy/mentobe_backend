from fastapi import APIRouter
from app.database import supabase
from app.models import SuccessResponse, ErrorResponse
from app.dependencies import get_password_hash
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

@router.post("/init", response_model=SuccessResponse)
async def init_system():
    """
    系统初始化接口
    用于创建初始管理员账号
    """
    logger.info("System initialization requested")
    
    # Check if admin user exists
    try:
        response = supabase.table("users").select("*").eq("email", "admin@mentobai.com").execute()
        
        if response.data:
            logger.info("Admin user already exists")
            admin_user = response.data[0]
            return SuccessResponse(data={
                "message": "管理员用户已存在",
                "user": {
                    "id": admin_user["id"],
                    "username": admin_user["username"],
                    "email": admin_user["email"]
                }
            })
        
        # Create admin user
        logger.info("Creating admin user...")
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
            logger.info(f"Admin user created successfully: {created_user['id']}")
            return SuccessResponse(data={
                "message": "管理员用户创建成功",
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
             logger.error("Failed to insert admin user")
             return ErrorResponse(success=False, error={"code": "DB_ERROR", "message": "创建管理员用户失败"})
            
    except Exception as e:
        logger.error(f"System initialization error: {e}")
        return ErrorResponse(success=False, error={"code": "DB_ERROR", "message": str(e)})
