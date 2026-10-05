from django.urls import path
from .views import (
    UserLoginView,
    UserLogoutView,
    UserPasswordChangeView,
    UserPasswordChangeDoneView,
    UserProfileView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CurrentUserAPIView,
)

app_name = 'users'

urlpatterns = [
    # Session-Based Web UI Authentication
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('password-change/', UserPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', UserPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('profile/', UserProfileView.as_view(), name='profile'),

    # REST Framework & JWT Token Authentication Endpoints
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/me/', CurrentUserAPIView.as_view(), name='current_user'),
]
