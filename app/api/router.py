from fastapi import APIRouter

from app.api.routes import auth as auth_r
from app.api.routes import users as users_r
from app.api.routes import chat as chat_r
from app.api.routes import conversations as conv_r
from app.api.routes import knowledge as know_r
from app.api.routes import faqs as faqs_r
from app.api.routes import tickets as tick_r
from app.api.routes import departments as dept_r
from app.api.routes import notifications as notif_r
from app.api.routes import feedback as fb_r
from app.api.routes import analytics as anal_r
from app.api.routes import staff as staff_r
from app.api.routes import admin as admin_r
from app.api.routes import health as health_r

api_router = APIRouter(prefix="")

api_router.include_router(auth_r.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_r.router, prefix="/users", tags=["Users"])
api_router.include_router(chat_r.router, prefix="/chat", tags=["Chat"])
api_router.include_router(conv_r.router, prefix="/chat", tags=["Conversations"])
api_router.include_router(know_r.router, prefix="/knowledge", tags=["Knowledge"])
api_router.include_router(faqs_r.router, prefix="/faqs", tags=["FAQs"])
api_router.include_router(tick_r.router, prefix="/tickets", tags=["Tickets"])
api_router.include_router(staff_r.router, prefix="/staff", tags=["Staff"])
api_router.include_router(dept_r.router, prefix="/departments", tags=["Departments"])
api_router.include_router(notif_r.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(fb_r.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(anal_r.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(admin_r.router, prefix="/admin", tags=["Admin"])
api_router.include_router(health_r.router, prefix="/health", tags=["Health"])

