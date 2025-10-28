from django.db import models

class Pricing(models.Model):
    name = models.CharField(max_length=250, blank=False, null=False)
    durations = (('Month', 'Month'),
                 ('Year', 'Year'),
                 ('Free', 'Free'),
                 )
    pricing_duration = models.CharField(choices=durations, max_length=250, blank=False, null=False)
    price = models.FloatField(blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    lengthy_summaries = models.BooleanField(default=False)
    lengthy_qa = models.BooleanField(default=False)
    audio_summary = models.BooleanField(default=True)
    user_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
