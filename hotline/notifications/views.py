from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render

from hotline.perms import permissions
from hotline.reports.models import Report

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

    reported = Report.objects.filter(Q(pk__in=request.session.get("report_ids", [])) | Q(created_by_id=user.pk))
    reported_querystring = "created_by_id:(%s)" % (" ".join(map(str, set(reported.values_list("created_by_id", flat=True)))))

    return render(request, "notifications/list.html", {
        "form": form,
        "user": user,
        "reported_querystring": reported_querystring,
        "invited_to": user.get_invited if not user.is_anonymous() else None,
        "reported": reported,
        "subscribed": user.get_subscriptions if not user.is_anonymous() else None,
        "open_and_claimed": user.get_open_and_claimed if not user.is_anonymous() else None,
        "unclaimed_reports": user.get_unclaimed if not user.is_anonymous() else None
    })
