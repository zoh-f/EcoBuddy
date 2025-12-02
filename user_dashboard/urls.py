from django.urls import path, include
from . import views
from django.contrib import admin
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView    
from django.conf import settings
from django.conf.urls.static import static
    
urlpatterns = [
    path("", views.home, name = 'home'),
    path("admin_page/", views.admin_page, name="admin_page"),
    path("logout/", views.logout_view, name="logout"),
    path("post_page/", views.posts_page, name="post_page"),
    path("create_post/", views.create_post, name="create_post"),

    # Account deletion routes
    path("settings/", views.account_settings, name="account_settings"),
    path("delete-account/", views.delete_account, name="delete_account"),

    # Moderation routes - using simple paths with query params
    path("moderation/", views.moderation_dashboard, name="moderation_dashboard"),
    path("moderation/flag/", views.flag_content, name="flag_content"),
    path("moderation/remove-post/", views.remove_post, name="remove_post"),
    path("moderation/remove-message/", views.remove_message, name="remove_message"),
    path("moderation/dismiss/", views.dismiss_flag, name="dismiss_flag"),

    # User suspension routes
    path("moderation/suspend/", views.suspend_user, name="suspend_user"),
    path("moderation/reinstate/", views.reinstate_user, name="reinstate_user"),
    path("moderation/suspended-users/", views.suspended_users_list, name="suspended_users_list"),
    path("account-suspended/", views.account_suspended, name="account_suspended"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)