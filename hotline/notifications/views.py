from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render

from hotline.perms import permissions
from hotline.reports.models import Invite, Report

from .forms import UserNotificationQueryForm, UserSubscriptionDeleteForm
from .models import UserNotificationQuery


@permissions.is_active
def create(request):
    query = request.GET.copy()
    try:
        query.pop("tabs")
    except KeyError:
        pass # no keyword called tabs, so that's fine.
    query = query.urlencode()
    instance = UserNotificationQuery(user=request.user, query=query)
    if request.method == "POST":
        form = UserNotificationQueryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved")
            return HttpResponseRedirect(reverse("reports-list") + "?" + request.GET.urlencode())
    else:
        form = UserNotificationQueryForm(instance=instance)

    return render(request, "notifications/create.html", {
        "form": form,
    })


@permissions.is_active
def list_(request):
    # all that awesome tabs stuff
    user = request.user

    if request.method == "POST":
        form = UserSubscriptionDeleteForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved")
            return redirect("notifications-list")
    else:
        form = UserSubscriptionDeleteForm(user=request.user)

    return render(request, "notifications/list.html", {
        "form": form,
        "user": user,
        "reported_querystring": user.get_reported_querystring,
        "invited_to": user.get_invited,
        "reported": user.get_reported,
        "subscribed": user.get_subscriptions,
        "open_and_claimed": user.get_open_and_claimed,
        "unclaimed_reports": user.get_unclaimed
    })
