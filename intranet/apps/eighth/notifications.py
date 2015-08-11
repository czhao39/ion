# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from intranet import settings
from ..users.models import User
from ..notifications.emails import email_send
from .models import EighthBlock, EighthSignup

logger = logging.getLogger(__name__)

def signup_status_email(user, next_blocks):
    em = user.emails[0] if user.emails and len(user.emails) >= 1 else user.tj_email
    if em:
        emails = [em]
    else:
        return False

    blocks = []
    issues = 0
    for blk in next_blocks:
        try:
            signup = EighthSignup.objects.get(user=user, scheduled_activity__block=blk)
        except EighthSignup.DoesNotExist:
            signup = None

        cancelled = False

        if not signup:
            issues += 1

        if signup and signup.scheduled_activity.cancelled:
            issues += 1
            cancelled = True
        blocks.append({
            "block": blk,
            "signup": signup,
            "cancelled": cancelled
        })

    block_date = next_blocks[0].date
    block_signup_time = next_blocks[0].signup_time
    if block_signup_time:
        block_signup_time = "{}:{}".format(block_signup_time.hour, block_signup_time.minute)

    date_str = block_date.strftime("%A, %B %-d")

    subject = "Signup Status for {}".format(date_str)

    # We can't build an absolute URI because this isn't being executed
    # in the context of a Django request
    base_url = "https://ion.tjhsst.edu/" #request.build_absolute_uri(reverse('index'))
    data = {
        "user": user,
        "blocks": blocks,
        "block_date": block_date,
        "date_str": date_str,
        "block_signup_time": block_signup_time,
        "base_url": base_url,
        "issues": issues
    }

    email_send("eighth/emails/signup_status.txt",
               "eighth/emails/signup_status.html",
               data, subject, emails)