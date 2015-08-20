import csv
import json
import sys
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.functional import curry

from hotline.comments.forms import CommentForm
from hotline.comments.models import Comment
from hotline.comments.perms import can_create_comment
from hotline.images.forms import get_image_formset
from hotline.images.models import Image
from hotline.notifications.models import UserNotificationQuery
from hotline.species.models import category_id_to_species_id_json

from .forms import (
    ConfirmForm,
    InviteForm,
    ReportForm,
    ReportSearchForm,
    SettingsForm,
)
from .models import Invite, Report
from .perms import can_manage_report, can_view_private_report, permissions


def list_(request):
    if request.user.is_active:
        template = "reports/list.html"
    else:
        template = "reports/list_public.html"

    # all that awesome tabs stuff
    user = request.user
    tab = request.GET.get('tabs') if request.GET.get('tabs') is not None else "search"

    form = ReportSearchForm(request.GET, user=request.user, report_ids=request.session.get("report_ids", []))

    # handle the case where they want to export the reports
    if request.user.is_active and request.GET.get("export") in ['kml', 'csv']:
        return _export(reports=form.results(page=1, items_per_page=sys.maxsize), format=request.GET['export'])

    reports = form.results(request.GET.get("page", 1))

    reports_json = []
    for report in reports:
        reports_json.append(report.to_json())

    return render(request, template, {
        "reports": reports,
        "form": form,
        "reports_json": json.dumps(reports_json),
        "tab": tab,
        "invited_to": user.get_invited,
        "reported": user.get_reported,
        "reported_querystring": user.get_reported_querystring,
        "subscribed": user.get_subscriptions,
        "open_and_claimed": user.get_open_and_claimed,
        "unclaimed_reports": user.get_unclaimed
    })


def _export(reports, format):
    """
    Returns an HttpResponse containing all the reports in the specified format
    """
    if format == "csv":
        response = HttpResponse("", content_type="text/csv")
        # maps a field name, to a function that gets the data for the field,
        # given a Report object
        fields = OrderedDict([
            ("Report ID", lambda report: report.pk),
            ("Category", lambda report: str(report.category)),
            ("Common Name", lambda report: report.species.name if report.species else ""),
            ("Scientific Name", lambda report: report.species.scientific_name if report.species else ""),
            ("Species Confirmed", lambda report: bool(report.actual_species)),
            ("Reported By", lambda report: str(report.created_by)),
            ("Reported On", lambda report: str(report.created_on)),
            ("Claimed By", lambda report: str(report.claimed_by)),
            ("Description", lambda report: report.description),
            ("Latitude", lambda report: report.point.y),
            ("Longitude", lambda report: report.point.x),
            ("EDRR Status", lambda report: report.edrr_status),
            ("Is Public", lambda report: report.is_public),
            ("Is Archived", lambda report: report.is_archived),
        ])
        writer = csv.DictWriter(response, fields.keys())
        writer.writeheader()
        for report in reports:
            row = {}
            for key, accessor in fields.items():
                row[key] = accessor(report)
            writer.writerow(row)
    elif format == "kml":
        response = HttpResponse(render_to_string("reports/export.kml", {
            "reports": reports
        }), content_type="text/csv")
    else:
        raise ValueError("%s in not a valid format" % format)

    response['Content-Disposition'] = 'attachment; filename="reports.%s"' % format
    return response


def create(request):
    """
    Render the public form for submitting reports
    """
    ImageFormSet = get_image_formset()

    if request.POST:
        form = ReportForm(request.POST, request.FILES)
        formset = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.none())
        if form.is_valid() and formset.is_valid():
            report = form.save(request=request)
            formset.save(user=report.created_by, fk=report)
            messages.success(request, "Report submitted successfully")
            request.session.setdefault("report_ids", []).append(report.pk)
            request.session.modified = True
            response = redirect("reports-detail", report.pk)
            # the template sets some cookies in JS that we want to clear when
            # the report is submitted. This means the next time they go to this
            # page, the map will be initialized with the defaults
            response.delete_cookie("center", request.get_full_path())
            response.delete_cookie("zoom", request.get_full_path())
            return response
    else:
        formset = ImageFormSet(queryset=Image.objects.none())
        form = ReportForm()

    return render(request, "reports/create.html", {
        "form": form,
        "category_id_to_species_id": category_id_to_species_id_json(),
        "formset": formset
    })


def detail(request, report_id):
    """
    This is a complex view that handles displaying all the information about a
    Report. It needs to take into account the user's role on the Report to
    determine whether to display the comment form, and which comments to
    display, etc. It also handles the management of the report by the expert
    who claimed it
    """
    report = get_object_or_404(Report, pk=report_id)

    if (report.pk in request.session.get("report_ids", []) and
            report.created_by.is_active and
            report.created_by_id != request.user.pk and
            not request.user.is_active):
        # if the report was created by an active user and they aren't logged in
        # as that user, force them to re-login
        return login_required(lambda request: None)(request)

    if (report.pk in request.session.get("report_ids", []) and
            not report.created_by.is_active and
            report.created_by_id != request.user.pk and
            not request.user.is_active):
        # if the user submitted the report, allow them to masquerade as that
        # user for the life of this request
        request.user = report.created_by

    if not report.is_public:
        if request.user.is_anonymous() or not can_view_private_report(request.user, report):
            raise PermissionDenied()

    # there are a bunch of forms that can be filled out on this page, by
    # default, they can't be filled out
    comment_form = None
    image_formset = None
    invite_form = None
    confirm_form = None
    settings_form = None
    # this tells us which form was filled out since there are many on the page
    submit_flag = request.POST.get("submit_flag")

    # process the comment form only if they are allowed to leave comments
    if can_create_comment(request.user, report):
        ImageFormSet = get_image_formset(user=request.user)
        PartialCommentForm = curry(CommentForm, user=request.user, report=report)
        if request.POST and submit_flag == CommentForm.SUBMIT_FLAG:
            image_formset = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.none())
            comment_form = PartialCommentForm(request.POST, request.FILES)
            if comment_form.is_valid() and image_formset.is_valid():
                comment = comment_form.save(request=request)
                image_formset.save(user=comment.created_by, fk=comment)
                messages.success(request, "Comment Added!")
                return redirect(request.get_full_path())
        else:
            comment_form = PartialCommentForm()
            image_formset = ImageFormSet(queryset=Image.objects.none())

    # handle all the management forms
    if can_manage_report(request.user, report):
        # Confirming the report form...
        if request.POST and submit_flag == ConfirmForm.SUBMIT_FLAG:
            confirm_form = ConfirmForm(request.POST, instance=report)
            if confirm_form.is_valid():
                confirm_form.save()
                messages.success(request, "Updated!")
                return redirect(request.get_full_path())
        else:
            confirm_form = ConfirmForm(instance=report)

        # Marking the report settings
        if request.POST and submit_flag == SettingsForm.SUBMIT_FLAG:
            settings_form = SettingsForm(request.POST, instance=report)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Updated!")
                return redirect(request.get_full_path())
        else:
            settings_form = SettingsForm(instance=report)

        # Inviting experts...
        if request.POST and submit_flag == InviteForm.SUBMIT_FLAG:
            invite_form = InviteForm(request.POST)
            if invite_form.is_valid():
                invite_report = invite_form.save(report=report, user=request.user, request=request)
                message = "%d invited" % (len(invite_report.invited))
                if invite_report.already_invited:
                    message += " (%d already invited)" % len(invite_report.already_invited)
                messages.success(request, message)
                return redirect(request.get_full_path())
        else:
            invite_form = InviteForm()

    # filter down the comments based on the user's permissions
    comments = Comment.objects.filter(report=report)
    images = Image.objects.filter(Q(report=report) | Q(comment__report=report))
    if request.user.is_anonymous():
        comments = comments.filter(visibility=Comment.PUBLIC)
        images = images.filter(visibility=Image.PUBLIC)
    elif request.user.is_active or Invite.objects.filter(user=request.user, report=report).exists():
        # no need to filter for these folks
        pass
    else:
        # the logged in user is the person who reported
        comments = comments.filter(Q(visibility=Comment.PUBLIC) | Q(visibility=Comment.PROTECTED))
        images = images.filter(Q(visibility=Image.PUBLIC) | Q(visibility=Image.PROTECTED))

    invites = list(i.user.email for i in Invite.objects.filter(report=report).select_related("user"))

    return render(request, "reports/detail.html", {
        "report": report,
        "comments": comments,
        "images": list(images),
        "category_id_to_species_id": category_id_to_species_id_json(),
        "invites": invites,
        # all the forms
        "image_formset": image_formset,
        "comment_form": comment_form,
        "settings_form": settings_form,
        "invite_form": invite_form,
        "confirm_form": confirm_form,
    })


@permissions.can_claim_report
def claim(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    if request.method == "POST" and (report.claimed_by is None or "steal" in request.POST):
        report.claimed_by = request.user
        report.save()
        return redirect("reports-detail", report.pk)

    return render(request, "reports/claim.html", {
        "report": report,
    })


@permissions.can_unclaim_report
def unclaim(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    if request.method == "POST":
        report.claimed_by = None
        report.save()
        return redirect("reports-detail", report.pk)

    return render(request, "reports/unclaim.html", {
        "report": report,
    })


def invited(request):
    user = request.user
    
    return render(request, 'reports/invited.html', {
        "user": user,
        "reported_querystring": user.get_reported_querystring,
        "invited_to": user.get_invited,
        "reported": user.get_reported,
        "subscribed": user.get_subscriptions,
        "open_and_claimed": user.get_open_and_claimed,
        "unclaimed_reports": user.get_unclaimed
    })
