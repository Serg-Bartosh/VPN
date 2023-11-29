from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import login_view, registration, profile_view, proxy_view, edit_profile

urlpatterns = [
    path("login/", login_view, name="login"),
    path("registration/", registration, name="registration"),
    path("logout/", LogoutView.as_view(next_page="main"), name="logout"),
    path("profile/", profile_view, name="profile"),
    path("proxy/<str:user_site_name>/<path:original_link>/", proxy_view, name="proxy"),
    path("edit_profile/", edit_profile, name="edit_profile"),
]
