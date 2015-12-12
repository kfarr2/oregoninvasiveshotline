import os, sys
import hashlib
import subprocess
from PIL import Image

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.hashers import (
    BasePasswordHasher,
    constant_time_compare,
)
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.core.signals import request_finished
from django.db import transaction
from django.db.models import Q
from django.dispatch import receiver
from django.utils.timezone import localtime, now


@receiver(request_finished)
def refresh_index(*args, **kwargs):
    # XXX: This is so terrible; it should be replaced with a cron job
    #      OR, at the very least, a hack that isn't so bad.

    """
    To avoid using a cron job to rebuild the elasticsearch index every night,
    we have this signal receiver do it. It's a little hacky, but we create a
    service user and use the last_login date to determine when to update the
    index
    """
    # we don't want to run this during unit tests
    if hasattr(mail, "outbox"):
        return

    with transaction.atomic():
        user, _ = get_user_model().objects.get_or_create(email="ELASTICSEARCH_USER_DONT_DELETE_ME@pdx.edu", is_staff=False, is_active=False)
        user = get_user_model().objects.select_for_update().filter(pk=user.pk).first()
        # we use the last_login field on the user to determine if an update is necessary
        if user.last_login is None or localtime(user.last_login).day < localtime(now()).day:
            user.last_login = now()
            user.save()
            call_command('rebuild_index', noinput=True, clopen=True)


# The sites framework is dumb. I don't want to hardcode the hostname of the
# site in the database. To avoid doing that, we monkey patch
# Site.objects.get_current so it uses our custom function that always returns a
# Site object with the proper domain
def get_current(request=None, _get_current=Site.objects.get_current):
    if request is not None:
        # fake a Site object, since we are too lazy to keep the database updated
        return Site(domain=request.get_host(), name=request.get_host(), pk=getattr(settings, "SITE_ID", 1))
    else:
        return _get_current(request)

Site.objects.get_current = get_current


def resize_image(input_path, output_path, width, height):
    """
    Takes the input_path, output_path, width and height,
    opens, copies, resizes and saves the new image.
    """
    size = (width, height)
    if input_path != output_path:
        try:
            img = Image.open(input_path)
            img.thumbnail(size)
            img.save(output_path)

        except IOError as e:
            print("cannot resize image at: ", input_path)


def get_tab_counts(user, report_ids):
    from .reports.models import Report, Invite
    from .notifications.models import UserNotificationQuery
    return {
        "subscribed": UserNotificationQuery.objects.filter(user_id=user.pk).count(),
        "invited_to": Invite.objects.filter(user_id=user.pk).count(),
        "reported": Report.objects.filter(Q(pk__in=report_ids) | Q(created_by_id=user.pk)).count(),
        "open_and_claimed": 0 if user.is_anonymous() else Report.objects.filter(claimed_by_id=user.pk, is_public=False, is_archived=False).count(),
        "unclaimed_reports": Report.objects.filter(
            claimed_by=None,
            is_public=False,
            is_archived=False
        ).count() if user.is_authenticated() and user.is_active else 0,
    }


# Monkey patch the PasswordResetForm so it doesn't just silently ignore people
# with unusable password. Anyone with an is_active account should be able to
# reset their password
def get_users(self, email):
    return get_user_model()._default_manager.filter(email__iexact=email, is_active=True)

PasswordResetForm.get_users = get_users


class RubyPasswordHasher(BasePasswordHasher):
    """
    A password hasher that re-hashes the passwords from the old site so they can be used here.
    Encryption (old): Sha256
    """
    algorithm = "RubyPasswordHasher"

    def verify(self, password, encoded):
        """
        Actually, I think the only thing we have to do here is check that
        encoded_2 == encrypted
        instead of password == encrypted
        """
        algorithm, _, _, hash = encoded.split('$', 3)
        assert algorithm == self.algorithm
        # here's the extra step
        hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return constant_time_compare(hash, hashed)
