from django.urls import path
from .views import SignupView, LoginView, ProfileView, MarkNotificationReadView, NotificationsListView, HomeAPIView, \
    AboutAPIView, SellerRegistrationView, approve_seller
from rest_framework_simplejwt.views import TokenRefreshView
from .views import OTPRequestView, OTPVerifyView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),


    # Home & About
    path('home/', HomeAPIView.as_view()),
    path('about/', AboutAPIView.as_view()),

    # Profile
    path("profile/", ProfileView.as_view(), name="profile"),

    # Notifications
    path('notifications/', NotificationsListView.as_view()),
    path('notifications/<int:pk>/read/', MarkNotificationReadView.as_view()),

    # Seller Registration
    path('seller/register/', SellerRegistrationView.as_view()),
    path("admin/approve-seller/<int:seller_id>/", approve_seller, name="approve-seller"),

]



#superuser details-Phone number: 8207712465
#Name: Aditya
#Email: adi@gmail.com
#pass-Adi@0411