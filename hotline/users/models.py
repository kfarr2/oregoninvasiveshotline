from urllib.parse import urlencode

from django.contrib.auth.models import AbstractBaseUser, UserManager
from django.contrib.sessions.models import Session
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q


class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    prefix = models.CharField(max_length=255)
    suffix = models.CharField(max_length=255)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, blank=True, help_text="Inactive users cannot login and cannot manage reports")
    is_staff = models.BooleanField(default=False, blank=True)
    affiliations = models.TextField(blank=True)
    biography = models.TextField(blank=True)
    photo = models.ImageField(upload_to="images", blank=True)

    USERNAME_FIELD = 'email'

    objects = UserManager()

    class Meta:
        db_table = "user"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        if self.last_name and self.first_name:
            return self.get_full_name()
        else:
            return self.email

    def get_avatar_url(self):
        if self.photo:
            return self.photo.url
        return reverse("users-avatar", args=[self.pk])

    def get_authentication_url(self, request, next=None):
        signer = Signer("user-authentication")
        sig = signer.sign(self.email)
        querystring = urlencode({
            "sig": sig,
            "next": next or '',
        })
        return request.build_absolute_uri(reverse("users-authenticate")) + "?" + querystring

    @classmethod
    def authenticate(cls, sig):
        signer = Signer("user-authentication")
        email = signer.unsign(sig)
        return cls.objects.get(email=email)

    # These methods are required to work with Django's admin
    def get_full_name(self):
        return self.last_name + ", " + self.first_name

    def get_short_name(self):
        return self.first_name + " " + self.last_name

    def get_proper_name(self):
        return ("%s %s %s %s" % (self.prefix, self.first_name, self.last_name, self.suffix)).strip()

    # we don't need granular permissions; all staff will have access to
    # everything
    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff

    def can_cloak_as(self, other_user):
        """
        This method is used by the `cloak` package to determine if a user is
        allowed to cloak as another user
        """
        return self.is_staff

    # Methods for dealing with reports in tabs.
    @property
    def get_reported(self):
        from hotline.reports.models import Report
        return Report.objects.filter(Q(created_by_id=self.pk))
        #Q(pk__in=Session.get("report_ids", [])) |

    @property
    def get_reported_querystring(self):
        return "created_by_id:(%s)" % (" ".join(map(str, set(self.get_reported.values_list("created_by_id", flat=True)))))


    @property
    def get_invited(self):
        from hotline.reports.models import Invite
        return [invite.report for invite in Invite.objects.filter(user_id=self.pk).select_related("report")]

    @property
    def get_open_and_claimed(self):
        from hotline.reports.models import Report
        return Report.objects.filter(claimed_by_id=self.pk, is_public=False, is_archived=False).exclude(claimed_by=None)

    @property
    def get_unclaimed(self):
        from hotline.reports.models import Report
        return Report.objects.filter(claimed_by=None, is_public=False, is_archived=False)

    @property
    def get_subscriptions(self):
        from hotline.notifications.models import UserNotificationQuery
        return UserNotificationQuery.objects.filter(user=self)

from .indexes import *  # noqa isort:skip
