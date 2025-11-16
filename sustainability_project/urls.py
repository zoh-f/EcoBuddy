"""
URL configuration for sustainability_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from user_dashboard import views
from user_info.views import public_profile, upsert_profile

urlpatterns = [
    path('admin/', admin.site.urls),
    # for user profiles
    path("profiles/<str:username>/", public_profile, name="public-profile"),
    path("profiles/upsert/", upsert_profile, name="upsert-profile"),
    path('accounts/', include('allauth.urls')), 
    path("admin_page/", views.admin_page, name="admin_page"),
    path("", views.home, name="home"),
    path("logout/", views.logout_view, name="logout"),
    path('', include('user_dashboard.urls')),
    path('messaging/', include('messaging.urls')),   
]   
