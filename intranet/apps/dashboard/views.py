# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import timezone
import logging
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from intranet import settings
from ..users.models import User
from ..schedule.views import schedule_context
from ..announcements.models import Announcement, AnnouncementRequest
from ..eighth.models import (
    EighthBlock, EighthSignup, EighthScheduledActivity
)

logger = logging.getLogger(__name__)


def gen_schedule(user, num_blocks=6):
    """Generate a list of information about a block and a student's
    current activity signup.

    Returns:
        schedule
        no_signup_today

    """
    no_signup_today = None
    schedule = []

    block = EighthBlock.objects.get_first_upcoming_block()
    if block is None:
        schedule = None
    else:
        surrounding_blocks = [block] + list(block.next_blocks()[:num_blocks-1])
        # Use select_related to reduce query count
        signups = EighthSignup.objects.filter(user=user).select_related("scheduled_activity__block", "scheduled_activity__activity")
        block_signup_map = {s.scheduled_activity.block.id: s.scheduled_activity for s in signups}

        for b in surrounding_blocks:
            current_sched_act = block_signup_map.get(b.id, None)
            if current_sched_act:
                current_signup = current_sched_act.title_with_flags
                current_signup_cancelled = current_sched_act.cancelled
            else:
                current_signup = None
                current_signup_cancelled = False

            # warning flag (red block text and signup link) if no signup today
            # cancelled flag (red activity text) if cancelled
            flags = "locked" if b.locked else "open"
            if (b.is_today() and not current_signup):
                flags += " warning"
            if current_signup_cancelled:
                flags += " cancelled"

            if current_signup_cancelled:
                # don't duplicate this info; already caught
                current_signup = current_signup.replace(" (Cancelled)", "")

            info = {
                "id": b.id,
                "block": b,
                "block_letter": b.block_letter,
                "current_signup": current_signup,
                "current_signup_cancelled": current_signup_cancelled,
                "locked": b.locked,
                "date": b.date,
                "flags": flags,
                "is_today": b.is_today(),
                "signup_time": b.signup_time,
                "signup_time_future": b.signup_time_future
            }
            schedule.append(info)

            if b.is_today() and not current_signup:
                no_signup_today = True

    return schedule, no_signup_today


def gen_sponsor_schedule(user, num_blocks=6):
    """Return a list of :class:`EighthScheduledActivity`\s in which the
    given user is sponsoring.

    Returns:
        sponsor_schedule
        no_attendance_today
    """

    no_attendance_today = None
    acts = []

    sponsor = user.get_eighth_sponsor()

    block = EighthBlock.objects.get_first_upcoming_block()
    if block is None:
        return [], False

    activities_sponsoring = (EighthScheduledActivity.objects.for_sponsor(sponsor)
                                                            .filter(block__date__gte=block.date))

    surrounding_blocks = [block] + list(block.next_blocks()[:num_blocks-1])
    for b in surrounding_blocks:
        num_added = 0
        sponsored_for_block = activities_sponsoring.filter(block=b)

        for schact in sponsored_for_block:
            acts.append(schact)
            if schact.block.is_today():
                if not schact.attendance_taken and schact.block.locked:
                    no_attendance_today = True

            num_added += 1

        if num_added == 0:
            # fake an entry for a block where there is no sponsorship
            acts.append({
                "block": b,
                "id": None,
                "fake": True
            })

    logger.debug(acts)
    return acts, no_attendance_today

def find_birthdays(request):
    """Return information on user birthdays."""
    today = datetime.now().date()
    actual_today = datetime.now().date()
    custom = False
    yr_inc = 0
    if "birthday_month" in request.GET and "birthday_day" in request.GET:
        try:
            mon = int(request.GET["birthday_month"])
            day = int(request.GET["birthday_day"])
            yr = today.year

            """ If searching a date that already happened this year, skip to the next year. """
            if mon < today.month or (mon == today.month and day < today.day):
                yr += 1
                yr_inc = 1

            today = datetime(yr, mon, day).date()
            custom = True
        except Exception:
            pass

    key = "birthdays:{}".format(today)

    cached = cache.get(key)

    if cached:
        logger.debug("Birthdays on {} loaded "
                     "from cache.".format(today))
        logger.debug(cached)
        return cached
    else:
        logger.debug("Loading and caching birthday info for {}".format(today))
        tomorrow = today + timedelta(days=1)

        data = {
            "custom": custom,
            "today": {
                "date": today,
                "users": [{
                    "id": u.id,
                    "full_name": u.full_name,
                    "grade": {
                        "name": u.grade.name
                    },
                    "age": u.age + yr_inc
                } for u in User.objects.users_with_birthday(today.month, today.day)],
                "inc": 0
            },
            "tomorrow": {
                "date": tomorrow,
                "users": [{
                    "id": u.id,
                    "full_name": u.full_name,
                    "grade": {
                        "name": u.grade.name
                    },
                    "age": u.age
                } for u in User.objects.users_with_birthday(tomorrow.month, tomorrow.day)],
                "inc": 1
            }
        }
        cache.set(key, data, timeout=60 * 60 * 24)
        return data





@login_required
def dashboard_view(request, show_widgets=True, show_expired=False):
    """Process and show the dashboard."""

    announcements_admin = request.user.has_admin_permission("announcements")

    if not show_expired:
        show_expired = ("show_expired" in request.GET)

    if announcements_admin and "show_all" in request.GET:
        # Show all announcements if user has admin permissions and the
        # show_all GET argument is given.
        announcements = (Announcement.objects.all()
                                             .prefetch_related("groups", "user", "event"))
    else:
        # Only show announcements for groups that the user is enrolled in.
        if show_expired:
            announcements = (Announcement.objects
                                     .visible_to_user(request.user)
                                     .prefetch_related("groups", "user", "event"))
        else:
            announcements = (Announcement.objects
                                         .visible_to_user(request.user)
                                         .filter(expiration_date__gt=timezone.now())
                                         .prefetch_related("groups", "user", "event"))

    # pagination
    if "start" in request.GET:
        start_num = int(request.GET.get("start"))
    else:
        start_num = 0

    display_num = 15
    end_num = start_num + display_num
    more_announcements = ((announcements.count() - start_num) > display_num)
    announcements = announcements[start_num:end_num]

    user_hidden_announcements = Announcement.objects.hidden_announcements(request.user)

    is_student = request.user.is_student
    eighth_sponsor = request.user.is_eighth_sponsor

    if show_widgets:
        dashboard_title = "Dashboard"
        dashboard_header = "Announcements"
    elif show_expired:
        dashboard_title = dashboard_header = "Announcement Archive"
    else:
        dashboard_title = dashboard_header = "Announcements"

    context = {
        "announcements": announcements,
        "announcements_admin": announcements_admin,
        "start_num": start_num,
        "end_num": end_num,
        "prev_page": start_num - display_num,
        "more_announcements": more_announcements,
        "hide_announcements": True,
        "user_hidden_announcements": user_hidden_announcements,
        "show_widgets": show_widgets,
        "show_expired": show_expired,
        "dashboard_title": dashboard_title,
        "dashboard_header": dashboard_header,
        "senior_graduation": settings.SENIOR_GRADUATION,
        "senior_graduation_year": settings.SENIOR_GRADUATION_YEAR,
        "birthdays": find_birthdays(request)
    }


    if show_widgets:
        if is_student:
            schedule, no_signup_today = gen_schedule(request.user)
        else:
            schedule = None
            no_signup_today = None

        if eighth_sponsor:
            sponsor_schedule, no_attendance_today = gen_sponsor_schedule(request.user)
        else:
            sponsor_schedule = None
            no_attendance_today = None

        context.update({
            "schedule": schedule,
            "no_signup_today": no_signup_today,
            "sponsor_schedule": sponsor_schedule,
            "no_attendance_today": no_attendance_today,
            "eighth_sponsor": eighth_sponsor,
        })

    if announcements_admin:
        all_waiting = AnnouncementRequest.objects.filter(posted=None, rejected=False)
        awaiting_teacher = all_waiting.filter(teachers_approved__isnull=True)
        awaiting_approval = all_waiting.filter(teachers_approved__isnull=False)

        context.update({
            "awaiting_teacher": awaiting_teacher,
            "awaiting_approval": awaiting_approval,
        })

    """ This isn't important and it adds a lot of overhead.
    # add to users_seen
    u = request.user
    for ann in announcements:
        u.announcements_seen.add(ann.user_map)
    u.save()
    """

    schedule = schedule_context(request)
    context.update(schedule)
    return render(request, "dashboard/dashboard.html", context)
