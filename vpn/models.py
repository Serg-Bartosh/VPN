from django.contrib.auth.models import User
from django.db import models


class Site(models.Model):
    url = models.URLField(max_length=255, null=False)
    name = models.CharField(max_length=255, null=False)
    domain = models.CharField(max_length=255)
    downloaded_data_size = models.FloatField(default=0)
    sent_data_size = models.FloatField(default=0)
    link_click_count = models.IntegerField(default=0)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user_id", "domain")
