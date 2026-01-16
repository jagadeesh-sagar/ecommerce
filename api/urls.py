from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework.authtoken import views
from . import views

urlpatterns = [

    path('login/', views.UserLoginView.as_view(), name='login'),  
    path('logout/', views.UserLogoutView.as_view(), name='logout'),   
    path('register/', views.UserRegistrationView.as_view(),name='register' ),
    path('refresh/', views.CookieTokenRefreshView.as_view(),name='refresh' ),
    path('csrf-token/', views.CSRFTokenView.as_view(), name='csrf-token'),


    # Useful for token-based auth (mostly for Postman / mobile / DRF clients)       
    # standard jwt tokens ( not useful for cookies)
    # path('token/auth/', views.obtain_auth_token),
    # path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  

]
