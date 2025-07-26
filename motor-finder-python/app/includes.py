from app.routes.user.router import auth_router as auth
from app.routes.category.router import category_router as category
from app.routes.security.captcha_router import captcha_router as captcha
from app.routes.admin.callback_router import callback_router as callback
from app.routes.admin.router import motorapi_router as motorapi
from app.routes.car.router import car_router as car
from app.routes.review.router import review_router as review    
from app.routes.frontend.router import api_router as frontend


def get_all_routers():
    return [
        auth,
        category,
        callback,
        captcha,
        motorapi,
        car,
        review,
        frontend
    ]