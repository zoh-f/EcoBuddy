from django.urls import path, include
from . import views
from django.contrib import admin
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView    
from django.conf import settings
from django.conf.urls.static import static
    
urlpatterns = [
    path("", views.home, name = 'home'),
    path("accounts/", include("allauth.urls")),
    path("admin_page/", views.admin_page, name="admin_page"),
    path("post_page/", views.posts_page, name="post_page"),
    path("create_post/", views.create_post, name="create_post"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)