from arcutils import will_be_deleted_with
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.functional import curry

from hotline.images.forms import get_image_formset
from hotline.images.models import Image

from .forms import CommentForm
from .models import Comment
from .perms import can_edit_comment


def edit(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    report = comment.report
    if report.pk in request.session.get("report_ids", []) and not report.created_by.is_active:
        request.user = report.created_by

    if request.user.is_anonymous():
        return login_required(lambda request: None)(request)

    if not can_edit_comment(request.user, comment):
        raise PermissionDenied()

    PartialCommentForm = curry(CommentForm, user=request.user, report=comment.report, instance=comment)
    # this is dumb, but the only way to pass an extra arg to the subform
    ImageFormSet = get_image_formset(user=request.user)

    if request.POST:
        form = PartialCommentForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.filter(comment=comment))
        if form.is_valid() and formset.is_valid():
            form.save(request=request)
            formset.save(user=comment.created_by, fk=comment)
            messages.success(request, "Comment Edited")
            return redirect("reports-detail", comment.report.pk)
    else:
        form = PartialCommentForm()
        formset = ImageFormSet(queryset=Image.objects.filter(comment=comment))

    return render(request, "comments/edit.html", {
        "comment": comment,
        "form": form,
        "formset": formset,
    })

def delete(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    report = comment.report
    if request.method == "POST":
        if can_edit_comment(request.user, comment):
            comment.delete()
            messages.success(request, "Comment Deleted")
        else:
            messages.warning(request, "Comment Is Not Yours To Edit")
        return redirect("reports-detail", report.pk)

    related_objects = list(will_be_deleted_with(comment))

    return render(request, "delete.html", {
        "object": comment,
        "will_be_deleted_with": related_objects,
    })
