"""
FastAPI Stripe Checkout Session API
文件位置：后端项目的 routes/stripe.py 或 app/api/stripe.py

功能：创建 Stripe Checkout Session，支持一次性支付
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/api/stripe", tags=["Stripe"])


# ===================== 配置 =====================

# 从环境变量读取 Stripe Secret Key
# 格式：sk_test_xxx（测试环境）或 sk_live_xxx（生产环境）
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith("sk_"):
    raise ValueError(
        "STRIPE_SECRET_KEY 未配置或无效。请设置环境变量：STRIPE_SECRET_KEY=sk_test_xxx"
    )

# Stripe API 基础 URL
STRIPE_API_BASE = "https://api.stripe.com"


# ===================== 数据模型 =====================

class CreateCheckoutSessionRequest(BaseModel):
    """创建支付会话请求模型"""
    price_id: str  # Stripe 价格ID，例如：price_1Sren7GVP93aj81Tr4d18z2S
    user_id: str  # 用户ID
    user_email: EmailStr  # 用户邮箱
    success_url: str  # 支付成功后的跳转URL
    cancel_url: str  # 支付取消后的跳转URL


class CheckoutSessionResponse(BaseModel):
    """支付会话响应模型"""
    session_id: str
    url: str


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error_code: Optional[str] = None
    message: str
    details: Optional[dict] = None


class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = True
    data: CheckoutSessionResponse


# ===================== API 端点 =====================

@router.post("/create-checkout-session", response_model=SuccessResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    http_request: Request
):
    """
    创建 Stripe Checkout Session

    功能：
    - 创建一个 Stripe 支付会话
    - 返回会话ID和支付页面URL
    - 支持一次性支付模式

    请求示例：
    ```json
    {
      "priceId": "price_1Sren7GVP93aj81Tr4d18z2S",
      "userId": "user-123",
      "userEmail": "user@example.com",
      "successUrl": "https://yourdomain.com/?payment=success",
      "cancelUrl": "https://yourdomain.com/pricing"
    }
    ```

    响应示例：
    ```json
    {
      "success": true,
      "data": {
        "sessionId": "cs_test_xxx",
        "url": "https://checkout.stripe.com/c/pay/xxx"
      }
    }
    ```

    错误响应：
    ```json
    {
      "success": false,
      "error": {
        "code": "STRIPE_API_ERROR",
        "message": "No such price: price_xxx"
      }
    }
    ```

    Stripe 错误码参考：
    - resource_missing: 资源不存在（如价格ID错误）
    - invalid_request_error: 请求参数无效
    - api_error: Stripe API 内部错误
    """
    try:
        print(f"[Stripe API] Creating checkout session: {request.user_id} ({request.user_email})")

        # 调用 Stripe API 创建 Checkout Session
        async with httpx.AsyncClient() as client:
            stripe_response = await client.post(
                f"{STRIPE_API_BASE}/v1/checkout/sessions",
                headers={
                    "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "mode": "payment",  # 一次性支付模式（如需订阅模式改为 "subscription"）
                    "payment_method_types": "card",
                    "line_items[0][price]": request.price_id,
                    "line_items[0][quantity]": 1,
                    "success_url": request.success_url,
                    "cancel_url": request.cancel_url,
                    "customer_email": request.user_email,
                    "client_reference_id": request.user_id,
                    "metadata[userId]": request.user_id,
                    "metadata[userEmail]": request.user_email,
                },
                timeout=30.0,
            )

        # 检查 Stripe API 响应
        stripe_data = stripe_response.json()

        if stripe_response.status_code != 200:
            error_detail = stripe_data.get("error", {})
            error_code = error_detail.get("code", "STRIPE_API_ERROR")
            error_message = error_detail.get("message", "Stripe API 调用失败")

            print(f"[Stripe API] Error: {error_code} - {error_message}")
            print(f"[Stripe API] Details: {error_detail}")

            raise HTTPException(
                status_code=stripe_response.status_code,
                detail={
                    "success": False,
                    "error": {
                        "code": error_code,
                        "message": error_message,
                        "details": error_detail,
                    },
                },
            )

        # 成功创建会话
        session_id = stripe_data.get("id")
        checkout_url = stripe_data.get("url")

        print(f"[Stripe API] Session created: {session_id}")

        return SuccessResponse(
            success=True,
            data=CheckoutSessionResponse(
                session_id=session_id,
                url=checkout_url,
            ),
        )

    except HTTPException:
        # 重新抛出 HTTPException
        raise

    except Exception as e:
        # 捕获其他异常
        print(f"[Stripe API] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "details": {"error": str(e)},
                },
            },
        )


# ===================== Webhook 端点（可选）=====================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe Webhook 端点

    功能：
    - 接收 Stripe 支付事件通知
    - 更新用户订阅状态
    - 增加用户配额

    支持的事件类型：
    - checkout.session.completed: 支付完成
    - payment_intent.succeeded: 支付成功
    - payment_intent.payment_failed: 支付失败

    注意：
    - 需要配置 STRIPE_WEBHOOK_SECRET 环境变量
    - 需要在 Stripe Dashboard 中配置 Webhook URL
    """
    import hashlib
    import hmac

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not webhook_secret:
        print("[Stripe Webhook] STRIPE_WEBHOOK_SECRET 未配置")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"message": "Webhook 未配置"}},
        )

    try:
        # 验证 Webhook 签名
        # 注意：生产环境应使用 stripe 库验证签名
        # 这里简化处理，实际部署时使用 stripe.Webhook.construct_event()
        pass

    except Exception as e:
        print(f"[Stripe Webhook] 签名验证失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": {"message": "签名验证失败"}},
        )

    # 解析事件数据
    try:
        import json
        event = json.loads(payload)
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})

        print(f"[Stripe Webhook] 收到事件: {event_type}")

        # 处理不同类型的事件
        if event_type == "checkout.session.completed":
            # 支付完成
            user_id = event_data.get("metadata", {}).get("userId")
            print(f"[Stripe Webhook] 用户 {user_id} 支付完成")
            # TODO: 更新用户订阅状态，增加配额
            # await update_user_subscription(user_id, event_data)

        elif event_type == "payment_intent.succeeded":
            # 支付成功
            print("[Stripe Webhook] 支付成功")

        elif event_type == "payment_intent.payment_failed":
            # 支付失败
            print("[Stripe Webhook] 支付失败")

        else:
            print(f"[Stripe Webhook] 未处理的事件类型: {event_type}")

        return {"success": True, "received": True}

    except Exception as e:
        print(f"[Stripe Webhook] 处理事件失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"message": "处理事件失败"}},
        )


# ===================== 导出路由 =====================

def get_stripe_router():
    """获取 Stripe 路由"""
    return router


# ===================== 测试代码 =====================

if __name__ == "__main__":
    # 快速测试代码
    import uvicorn

    print("=" * 60)
    print("FastAPI Stripe API 测试服务器")
    print("=" * 60)
    print("\n配置检查:")
    print(f"  STRIPE_SECRET_KEY: {'已配置' if STRIPE_SECRET_KEY else '未配置'}")
    print(f"  长度: {len(STRIPE_SECRET_KEY)} 字符")

    if not STRIPE_SECRET_KEY:
        print("\n❌ 错误: 请先配置 STRIPE_SECRET_KEY 环境变量")
        print("   示例: export STRIPE_SECRET_KEY=sk_test_xxx")
        exit(1)

    print("\n启动测试服务器...")
    print("  URL: http://localhost:8901/api/stripe/create-checkout-session")
    print("  文档: http://localhost:8901/docs")

    # 创建测试应用
    from fastapi import FastAPI
    app = FastAPI(title="Stripe API", version="1.0.0")
    app.include_router(router)

    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8901,
        log_level="info",
    )
