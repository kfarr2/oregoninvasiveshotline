import urllib.parse
from unittest.mock import Mock, patch

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy.mommy import make, prepare

from hotline.reports.models import Invite, Report

from .forms import LoginForm, UserForm
from .models import User


class AuthenticateViewTest(TestCase):
    def test_bad_signature_redirects_to_home(self):
        response = self.client.get(reverse("users-authenticate") + "?sig=asfd")
        self.assertRedirects(response, reverse("home"))

    def test_active_or_invited_users_are_logged_in(self):
        # test for an invited user
        invite = make(Invite)
        url = invite.user.get_authentication_url(request=Mock(build_absolute_uri=lambda a: a))
        response = self.client.get(url)
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

        # test for an active user
        user = make(User, is_active=True)
        url = user.get_authentication_url(request=Mock(build_absolute_uri=lambda a: a))
        response = self.client.get(url)
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

    def test_report_ids_session_variable_is_populated(self):
        user = make(User, is_active=False)
        report = make(Report, created_by=user)
        url = user.get_authentication_url(request=Mock(build_absolute_uri=lambda a: a))
        response = self.client.get(url)
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertIn(report.pk, self.client.session['report_ids'])


class UserHomeViewTest(TestCase):
    def test_fully_anonymous_users_sent_away(self):
        response = self.client.get(reverse("users-home"))
        self.assertRedirects(response, reverse("home"))

    def test_anonymous_user_with_report_ids_session_variable(self):
        # they should be able to see the reports they submitted that are in the
        # session var
        r1 = make(Report)
        r2 = make(Report)
        make(Report)  # this report shouldn't show up in the reported queryset
        session = self.client.session
        session['report_ids'] = [r1.pk, r2.pk]
        session.save()

        response = self.client.get(reverse("users-home"))
        self.assertTrue(set([r1, r2]) == set(response.context['reported']))


class UserFormTest(TestCase):
    """
    Tests for the UserForm
    """
    def test_password_field_only_when_user_being_created(self):
        """
        The password field should only be on the form if the user is being
        created (not edited)
        """
        form = UserForm(user=prepare(User))
        self.assertIn("password", form.fields)

        form = UserForm(instance=make(User), user=prepare(User))
        self.assertNotIn("password", form.fields)

    def test_your_dangerous_fields_are_not_editable(self):
        """
        Fields like is_active and is_staff should not be changable if the user
        is editing himself
        """
        user = make(User, is_staff=True)
        form = UserForm(user=user, instance=user)
        self.assertNotIn("is_active", form.fields)
        self.assertNotIn("is_staff", form.fields)

        # if someone is editing someone else, they can update those fields
        other_user = make(User)
        form = UserForm(instance=other_user, user=user)
        self.assertIn("is_active", form.fields)
        self.assertIn("is_staff", form.fields)

    def test_non_staffers_cannot_set_some_fields(self):
        """
        Some fields should not be editable by non-staffers
        """
        user = make(User, is_staff=False)
        form = UserForm(user=user, instance=user)
        self.assertNotIn("is_staff", form.fields)

    def test_save_sets_the_password_for_new_users(self):
        """
        If the user is being created, the password should be updated
        """
        # to avoid having to generate valid data for this form, we mock up the
        # superclass's save method and the form's cleaned_data
        with patch("hotline.users.forms.forms.ModelForm.save") as mock:
            user = prepare(User)
            form = UserForm(instance=user, user=make(User))
            form.cleaned_data = {"password": "foobar"}

            form.save()

            self.assertTrue(user.check_password("foobar"))
            # ensure the superclass was called (which actually saves the model)
            self.assertTrue(mock.called)


class UserTest(TestCase):
    """
    Tests for the User model
    """
    def test_str(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(str(user), "bar, foo")
        # the str method should fall back on the email address if a part of
        # their name is blank
        user = prepare(User, first_name="", last_name="bar")
        self.assertEqual(str(user), user.email)

    def test_get_full_name(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(user.get_full_name(), "bar, foo")

    def test_get_short_name(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(user.get_short_name(), "foo bar")

    def test_has_perm(self):
        """Staff members have all Django admin perms"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_perm("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_perm("foo"), user)

    def test_has_module_perms(self):
        """Staff members have all Django admin perms"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_module_perms("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_module_perms("foo"), user)

    def test_can_cloak_as(self):
        """Only staffers can cloak"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_module_perms("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_module_perms("foo"), user)

    def test_get_proper_name(self):
        user = prepare(User, prefix="Mr.", first_name="Foo", last_name="Bar", suffix="PHD")
        self.assertEqual(user.get_proper_name(), "Mr. Foo Bar PHD")
        user = prepare(User, first_name="Foo", last_name="Bar", prefix="", suffix="")
        self.assertEqual(user.get_proper_name(), "Foo Bar")

    def test_get_authentication_url_and_authenticate(self):
        u = make(User)

        def build_absolute_uri(arg):
            return "http://example.com" + arg

        url = u.get_authentication_url(request=Mock(build_absolute_uri=build_absolute_uri), next="lame")
        parts = urllib.parse.urlparse(url)
        self.assertEqual(parts.path, reverse("users-authenticate"))
        query = urllib.parse.parse_qs(parts.query)
        self.assertEqual(query['next'][0], "lame")
        self.assertEqual(u, User.authenticate(query['sig'][0]))


class LoginFormTest(TestCase):
    def test_clean_email_raises_validation_error_for_non_existing_user(self):
        form = LoginForm({
            "email": "foo@pdx.edu"
        })
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error("email"))

    def test_save_sends_email_to_user_with_login_link(self):
        user = make(User)
        form = LoginForm({
            "email": user.email
        })
        self.assertTrue(form.is_valid())
        with patch("hotline.users.forms.User.get_authentication_url", return_value="foobarius"):
            form.save(request=Mock())
            self.assertTrue(len(mail.outbox), 1)
            self.assertIn("foobarius", mail.outbox[0].body)


class LoginViewTest(TestCase):
    def test_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_logging_in_via_email_sends_an_email(self):
        user = make(User)
        response = self.client.post(reverse("login"), {
            "email": user.email,
            "form": "OTHER_LOGIN",
        })
        self.assertTrue(len(mail.outbox), 1)
        self.assertRedirects(response, reverse("login"))
