# ebay_oauth/urls.py
from django.urls import path
from .views import ebay_login, ebay_callback, ebay_notification, new_path_view, get_seller_info, get_listings, get_sales, dashboard

urlpatterns = [
    path('ebay/login/', ebay_login, name='ebay_login'),
    path('ebay/callback/', ebay_callback, name='ebay_callback'),
    path('ebay/notification/', ebay_notification, name='ebay_notification'),
    path('new/path/', new_path_view, name='new_path_view'),
    path('get_seller_info/<str:token>/', get_seller_info, name='get_seller_info'),
    path('get_listings/', get_listings, name='get_listings'),
    path('get_sales/', get_sales, name='get_sales'),
    path('dashboard/', dashboard, name='dashboard'),
]
