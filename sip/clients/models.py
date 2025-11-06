from django.contrib.auth.models import User
from django.db import models

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    storage_path = models.CharField(max_length=255, unique=True)
    quota_limit = models.CharField(max_length=50, help_text="e.g. 5G, 500M")

    def __str__(self):
        return self.user.username

class ClientFile(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=255)
    size = models.FloatField()  # MB
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.client.user.username})"
