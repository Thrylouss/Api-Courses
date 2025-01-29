from django.urls import path, re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import SimpleRouter

from . import views

schema_view = get_schema_view(
    openapi.Info(
        title="Project API",
        default_version="v1",
        description="Example API",
    ),
    public=True,
    permission_classes=([permissions.AllowAny,]),
)

router = SimpleRouter()
router.register("phone-verification", views.GetVerificationCode, basename="phone-verification")


urlpatterns = [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),

    path("auth/register-phone/", views.UserRegister.as_view(), name="register"),
    path("auth/verify-code/", views.VerifyCode.as_view(), name="verify"),
    path("auth/login/", views.UserLogin.as_view(), name="login"),

    path('user/update/', views.UpdateUserData.as_view(), name='update_user'),
    path('user/change-password/', views.ChangePasswordView.as_view(), name='delete_user'),
    path('user/forgot-password/', views.RequestPasswordResetView.as_view(), name='forgot_password'),
    path('user/forgot-password/verify/', views.VerifyResetCodeView.as_view(), name='forgot_password_verify'),
    path('user/forgot-password/confirm/', views.ResetPasswordView.as_view(), name='forgot_password_confirm'),

    path("", include(router.urls)),
]
