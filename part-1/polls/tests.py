import datetime

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import QuestionAdmin
from .models import Choice, Profile, Question


def create_question(question_text, days, user=None):
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time, created_by=user)

class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_future_question(self):
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_and_past_question(self):
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_two_past_questions(self):
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )

class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        past_question = create_question(question_text="Past Question.", days=-5)
        url = reverse("polls:detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)

class ProfileTests(TestCase):
    def test_new_user_gets_profile(self):
        user = User.objects.create_user(username="alice", password="pass")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsNotNone(user.profile.uuid)

    def test_profile_uuid_is_unique(self):
        user1 = User.objects.create_user(username="alice", password="pass")
        user2 = User.objects.create_user(username="bob", password="pass")
        self.assertNotEqual(user1.profile.uuid, user2.profile.uuid)


class AdminOwnershipTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.user_a = User.objects.create_user(username="alice", password="pass", is_staff=True)
        self.user_b = User.objects.create_user(username="bob", password="pass", is_staff=True)
        self.q_a = create_question("Alice's question", days=-1, user=self.user_a)
        self.q_b = create_question("Bob's question", days=-1, user=self.user_b)

    def _get_queryset_for(self, user):
        request = self.factory.get("/admin/polls/question/")
        request.user = user
        ma = QuestionAdmin(Question, self.site)
        return ma.get_queryset(request)

    def test_user_sees_only_own_questions(self):
        qs_a = self._get_queryset_for(self.user_a)
        self.assertIn(self.q_a, qs_a)
        self.assertNotIn(self.q_b, qs_a)

    def test_other_user_sees_only_their_questions(self):
        qs_b = self._get_queryset_for(self.user_b)
        self.assertIn(self.q_b, qs_b)
        self.assertNotIn(self.q_a, qs_b)

    def test_save_model_sets_created_by(self):
        request = self.factory.post("/admin/polls/question/add/")
        request.user = self.user_a
        ma = QuestionAdmin(Question, self.site)
        new_q = Question(question_text="New?", pub_date=timezone.now())
        ma.save_model(request, new_q, None, change=False)
        self.assertEqual(new_q.created_by, self.user_a)


class ResultsPageTests(TestCase):
    def test_results_page_shows_thank_you(self):
        q = create_question("Favourite colour?", days=-1)
        Choice.objects.create(question=q, choice_text="Red", votes=3)
        url = reverse("polls:results", args=(q.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank you")
        self.assertNotIn("chart_labels", response.context)

    def test_vote_creates_vote_record(self):
        from .models import Vote
        q = create_question("Best colour?", days=-1)
        c = Choice.objects.create(question=q, choice_text="Red", votes=0)
        self.client.post(reverse("polls:vote", args=(q.id,)), {"choice": c.id})
        self.assertEqual(Vote.objects.filter(question=q, choice=c).count(), 1)


class AdminAnalyticsTests(TestCase):
    def test_admin_change_view_has_vote_details(self):
        owner = User.objects.create_user(username="ad123", password="pass", is_staff=True, is_superuser=True)
        self.client.force_login(owner)
        q = create_question("Admin poll?", days=-1, user=owner)
        c = Choice.objects.create(question=q, choice_text="Yes", votes=0)
        from .models import Vote
        Vote.objects.create(question=q, choice=c, voter=owner)
        url = f"/admin/polls/question/{q.id}/change/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("vote_details", response.context)
        details = response.context["vote_details"]
        self.assertEqual(details[0]["count"], 1)
        self.assertIn("ad123", details[0]["voters"])
