import datetime
import uuid

from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return f"{self.user.username} ({self.uuid})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="questions",
    )

    def __str__(self):
        return self.question_text

    @admin.display(
        boolean=True,
        ordering="pub_date",
        description="Published recently?",
    )
    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text


class Analytics(Question):
    class Meta:
        proxy = True
        verbose_name = "Analytics"
        verbose_name_plural = "Analytics"


class Vote(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="vote_records")
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name="vote_records")
    voter = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="poll_votes")
    voted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        voter_name = self.voter.username if self.voter else "Anonymous"
        return f"{voter_name} \u2192 {self.choice.choice_text}"
