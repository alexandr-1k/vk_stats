from django.contrib import admin
from django.urls import path, include
from .views import login_view, app_view, input_view

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path("accounts/", include("allauth.urls")),

    path("", login_view, name="home"),
    path("app/", app_view, name='app'),
    path("result/", input_view, name='result'),


] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
