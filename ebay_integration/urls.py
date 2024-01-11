# ebay_integration/urls.py
from django.contrib import admin
from django.urls import path, include
from ebay_oauth.views import (
    ebay_login,
    ebay_callback,
    ebay_notification,
    new_path_view,
    get_seller_info,
    get_listings,
    get_sales,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ebay/login/', ebay_login, name='ebay_login'),
    path('ebay/callback/', ebay_callback, name='ebay_callback'),
    path('ebay/notification/', ebay_notification, name='ebay_notification'),
    path('new_path/', new_path_view, name='new_path'),  # Updated name here
    path('get_seller_info/', get_seller_info, name='get_seller_info'),
    path('get_listings/', get_listings, name='get_listings'),
    path('get_sales/', get_sales, name='get_sales'),
    path('', include('ebay_oauth.urls')),
]
