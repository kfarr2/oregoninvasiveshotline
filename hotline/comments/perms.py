from hotline.reports.models import Report
from hotline.reports.perms import can_view_private_report

from ..perms import permissions
from .models import Comment


@permissions.register(model=Report)
def can_create_comment(user, report):
    return can_view_private_report(user, report)

@permissions.register(model=Comment)
def can_edit_comment(user, comment):
    return user.is_staff or comment.created_by == user

@permissions.register(model=Comment)
def can_delete_comment(user, comment):
    return comment.pk is not None and can_edit_comment(user, comment)
