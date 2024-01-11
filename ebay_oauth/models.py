# ebay_oauth/models.py
from django.db import models


class Token(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    platform = models.CharField(max_length=255)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expiry = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} - {self.platform}"


class SellerInfo(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    platform = models.CharField(max_length=255)
    seller_info = models.JSONField()

    def __str__(self):
        return f"{self.user.username} - {self.platform} Seller Info"
