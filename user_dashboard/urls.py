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
    path("post/<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("post/<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("post/<int:post_id>/delete/", views.delete_post, name="delete_post"),
    path('finish-onboarding/', views.finish_onboarding, name='finish_onboarding'),

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

    # Social Feed routes
    path("feed/", views.public_feed, name="public_feed"),

    # User profile routes
    path("profile/<str:username>/", views.user_profile, name="user_profile"),
    path("search/", views.user_search, name="user_search"),

    # Friend system routes
    path("friends/", views.friends_list, name="friends_list"),
    path("friends/send/", views.send_friend_request, name="send_friend_request"),
    path("friends/accept/", views.accept_friend_request, name="accept_friend_request"),
    path("friends/reject/", views.reject_friend_request, name="reject_friend_request"),
    path("friends/unfriend/", views.unfriend, name="unfriend"),

    # Drafts routes
    path("drafts/", views.drafts_page, name="drafts_page"),
    path("drafts/publish/", views.publish_draft, name="publish_draft"),

    # Notifications routes
    path("notifications/", views.notifications_page, name="notifications"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)