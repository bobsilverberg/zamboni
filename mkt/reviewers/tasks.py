from django.conf import settings

from celeryutils import task
from tower import ugettext as _

import amo
from amo.storage_utils import move_stored_file
from amo.utils import LocalFileStorage, send_mail_jinja
import mkt.constants.reviewers as rvw


@task
def send_mail(cleaned_data, theme_lock):
    """
    Send emails out for respective review actions taken on themes.
    """
    theme = cleaned_data['theme']
    action = cleaned_data['action']
    comment = cleaned_data['comment']
    reject_reason = cleaned_data['reject_reason']

    reason = None
    if reject_reason:
        reason = rvw.THEME_REJECT_REASONS[reject_reason]
    elif action == rvw.ACTION_DUPLICATE:
        reason = _('Duplicate Submission')

    emails = set(theme.addon.authors.values_list('email', flat=True))
    cc = settings.THEMES_EMAIL
    context = {
        'theme': theme,
        'base_url': settings.SITE_URL,
        'reason': reason,
        'comment': comment
    }

    subject = None
    if action == rvw.ACTION_APPROVE:
        subject = _('Thanks for submitting your Theme')
        template = 'reviewers/themes/emails/approve.html'
        theme.addon.update(status=amo.STATUS_PUBLIC)

    elif action == rvw.ACTION_REJECT:
        subject = _('A problem with your Theme submission')
        template = 'reviewers/themes/emails/reject.html'

    elif action == rvw.ACTION_DUPLICATE:
        subject = _('A problem with your Theme submission')
        template = 'reviewers/themes/emails/reject.html'

    elif action == rvw.ACTION_FLAG:
        subject = _('Theme submission flagged for review')
        template = 'reviewers/themes/emails/flag_reviewer.html'

        # Send the flagged email to themes email.
        emails = [settings.THEMES_EMAIL]
        cc = None

    elif action == rvw.ACTION_MOREINFO:
        subject = _('A question about your Theme submission')
        template = 'reviewers/themes/emails/moreinfo.html'
        context['reviewer_email'] = theme_lock.reviewer.email

    send_mail_jinja(subject, template, context,
                    recipient_list=emails, cc=cc,
                    from_email=settings.ADDONS_EMAIL,
                    headers={'Reply-To': settings.THEMES_EMAIL})


@task
def approve_rereview(theme):
    """Replace original theme with pending theme on filesystem."""
    # If reuploaded theme, replace old theme design.
    storage = LocalFileStorage()
    rereview = theme.rereviewqueuetheme_set.all()
    reupload = rereview[0]

    move_stored_file(
        reupload.header_path, reupload.original_header_path,
        storage=storage)
    move_stored_file(
        reupload.footer_path, reupload.original_footer_path,
        storage=storage)
    rereview.delete()


@task
def reject_rereview(theme):
    """Replace original theme with pending theme on filesystem."""
    storage = LocalFileStorage()
    rereview = theme.rereviewqueuetheme_set.all()
    reupload = rereview[0]

    storage.delete(reupload.header_path)
    storage.delete(reupload.footer_path)
    rereview.delete()
