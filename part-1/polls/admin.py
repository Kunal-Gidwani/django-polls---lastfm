from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse

from .models import Analytics, Choice, Profile, Question, Vote
from .validators import USERNAME_EXISTS_MSG, username_already_exists, validate_username_value


class StrictUserCreationForm(UserCreationForm):
    def clean_username(self):
        username = self.cleaned_data.get("username")
        validate_username_value(username)
        if username_already_exists(username):
            raise ValidationError(USERNAME_EXISTS_MSG)
        return username


class StrictUserChangeForm(UserChangeForm):
    def clean_username(self):
        username = self.cleaned_data.get("username")
        validate_username_value(username)
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(USERNAME_EXISTS_MSG)
        return username


class StrictUserAdmin(BaseUserAdmin):
    add_form = StrictUserCreationForm
    form = StrictUserChangeForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
                "description": "Username must be exactly 5 characters.",
            },
        ),
    )


admin.site.unregister(User)
admin.site.register(User, StrictUserAdmin)


class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "uuid"]
    readonly_fields = ["uuid", "user"]

    def has_add_permission(self, request):
        return False


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["question_text", "created_by"]}),
        ("Date information", {"fields": ["pub_date"], "classes": ["collapse"]}),
    ]
    readonly_fields = ["created_by"]
    inlines = [ChoiceInline]
    list_display = ["question_text", "pub_date", "was_published_recently", "owner_username"]
    list_filter = ["pub_date"]
    search_fields = ["question_text"]

    def owner_username(self, obj):
        return obj.created_by.username if obj.created_by else "-"
    owner_username.short_description = "Owner"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(created_by=request.user)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        question = self.get_object(request, object_id)
        if question:
            vote_details = []
            for choice in question.choice_set.all():
                voters = [
                    v.voter.username if v.voter else "Anonymous"
                    for v in choice.vote_records.select_related("voter")
                ]
                vote_details.append({
                    "choice_text": choice.choice_text,
                    "count": len(voters),
                    "voters": voters,
                    "percent": 0,
                })
            total_votes = sum(d["count"] for d in vote_details)
            for d in vote_details:
                d["percent"] = round(d["count"] / total_votes * 100, 1) if total_votes else 0
            extra_context["vote_details"] = vote_details
            extra_context["total_votes"] = total_votes
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


class VoteAdmin(admin.ModelAdmin):
    list_display = ["voter", "question", "choice", "voted_at"]
    list_filter = ["question"]
    readonly_fields = ["voter", "question", "choice", "voted_at"]

    def has_add_permission(self, request):
        return False


class AnalyticsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        questions = Question.objects.filter(created_by=request.user).prefetch_related("choice_set")
        analytics_data = []
        for q in questions:
            vote_details = []
            for choice in q.choice_set.all():
                voters = [
                    v.voter.username if v.voter else "Anonymous"
                    for v in choice.vote_records.select_related("voter")
                ]
                vote_details.append({
                    "choice_text": choice.choice_text,
                    "count": len(voters),
                    "percent": 0,
                })
            total = sum(d["count"] for d in vote_details)
            for d in vote_details:
                d["percent"] = round(d["count"] / total * 100, 1) if total else 0
            analytics_data.append({
                "question": q,
                "total_votes": total,
                "vote_details": vote_details,
            })
        context = {
            **self.admin_site.each_context(request),
            "title": "Poll Analytics",
            "analytics_data": analytics_data,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/polls/analytics.html", context)


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Analytics, AnalyticsAdmin)
