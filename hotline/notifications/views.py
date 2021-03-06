from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render

from hotline.perms import permissions
from hotline.utils import get_tab_counts

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

    report_ids = request.session.get("report_ids", [])
    tab_context = get_tab_counts(user, report_ids)

    if request.method == "POST":
        form = UserSubscriptionDeleteForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved")
            return redirect("notifications-list")
    else:
        form = UserSubscriptionDeleteForm(user=request.user)

    return render(request, "notifications/list.html", dict({
        "form": form,
    }, **tab_context))
