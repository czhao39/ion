# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import datetime
from calendar import monthrange
from .models import Event
from .forms import EventForm
from ..auth.decorators import events_admin_required
from intranet import settings
from django.core import exceptions
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

logger = logging.getLogger(__name__)

@login_required
def events_view(request):
    """
        Events homepage. Shows a list of events occurring in the next week, month, and future.

    """
    #if settings.PRODUCTION and not request.user.has_admin_permission('events'):
    #    # In production, go to not ready page.
    #    return render(request, "events/not_ready.html")

    viewable_events = (Event.objects
                            .visible_to_user(request.user)
                            .prefetch_related("groups"))

    # get date objects for week and month
    today = datetime.date.today()
    delta = today - datetime.timedelta(days=today.weekday())
    this_week = (delta, delta + datetime.timedelta(days=7))
    this_month = (this_week[1], this_week[1] + datetime.timedelta(days=31))

    context = {
        "events": [
            {
                "title": "This week",
                "events": viewable_events.filter(time__gt=this_week[0], time__lt=this_week[1])
            },
            {
                "title": "This month",
                "events": viewable_events.filter(time__gt=this_month[0], time__lt=this_month[1])
            },
            {
                "title": "Future",
                "events": viewable_events.filter(time__gt=this_month[1])
            }
        ],
        "is_events_admin": request.user.has_admin_permission('events'),
        "show_attend": True
    }
    return render(request, "events/home.html", context)

@login_required
def join_event_view(request, id):
    """
        Join event page. If a POST request, actually add or remove the attendance of
        the current user. Otherwise, display a page with confirmation.

        id: event id

    """
    #if settings.PRODUCTION and not request.user.has_admin_permission('events'):
    #    return render(request, "events/not_ready.html")

    event = get_object_or_404(Event, id=id)

    if request.method == "POST":
        if "attending" in request.POST:
            attending = request.POST.get("attending")
            attending = (attending == "true")

            if attending:
                event.attending.add(request.user)
            else:
                event.attending.remove(request.user)

            return redirect("events")

    context = {
        "event": event,
        "is_events_admin": request.user.has_admin_permission('events'),
    }
    return render(request, "events/join_event.html", context)

@login_required
def event_roster_view(request, id):
    """
        Show the event roster. Users with hidden eighth period permissions will not be
        displayed. Users will be able to view all other users, along with a count of the
        number of hidden users. (Same as 8th roster page.) Admins will see a full roster
        at the bottom.

        id: event id

    """

    #if settings.PRODUCTION and not request.user.has_admin_permission('events'):
    #    return render(request, "events/not_ready.html")

    event = get_object_or_404(Event, id=id)
    
    full_roster = list(event.attending.all())
    viewable_roster = []
    num_hidden_members = 0
    for p in full_roster:
        if p.can_view_eighth:
            viewable_roster.append(p)
        else:
            num_hidden_members += 1

    context = {
        "event": event,
        "viewable_roster": viewable_roster,
        "full_roster": full_roster,
        "num_hidden_members": num_hidden_members,
        "is_events_admin": request.user.has_admin_permission('events'),
    }
    return render(request, "events/roster.html", context)

@login_required
def add_event_view(request):
    """
        Add event page. Currently, there is no credential checking; any user may create
        an event. This may change.

    """
    #if settings.PRODUCTION and not request.user.has_admin_permission('events'):
    #    return render(request, "events/not_ready.html")

    if request.method == "POST":
        form = EventForm(request.POST)
        logger.debug(form)
        if form.is_valid():
            obj = form.save()
            obj.user = request.user
            obj.save()
            messages.success(request, "Successfully added event.")
            return redirect("events")
        else:
            messages.error(request, "Error adding event")
    else:
        form = EventForm()
    return render(request, "events/add_modify.html", {"form": form, "action": "add"})

@login_required
def modify_event_view(request, id=None):
    """
        Modify event page. You may only modify an event if you were the creator or you are an
        administrator.

        id: event id

    """
    event = get_object_or_404(Event, id=id)

    if not request.user.has_admin_permission('events') and event.user != request.user:
        raise exceptions.PermissionDenied

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        logger.debug(form)
        if form.is_valid():
            obj = form.save()
            obj.user = request.user
            obj.save()
            messages.success(request, "Successfully modified event.")
            #return redirect("events")
        else:
            messages.error(request, "Error adding event.")
    else:
        form = EventForm(instance=event)
    return render(request, "events/add_modify.html", {"form": form, "action": "modify", "id": id})


@login_required
def delete_event_view(request, id):
    """
        Delete event page. You may only delete an event if you were the creator or you are an
        administrator. Confirmation page if not POST.

        id: event id

    """
    event = get_object_or_404(Event, id=id)
    if not request.user.has_admin_permission('events') and event.user != request.user:
        raise exceptions.PermissionDenied

    if request.method == "POST":
        try:
            event.delete()
            messages.success(request, "Successfully deleted event.")
        except Event.DoesNotExist:
            pass

        return redirect("events")
    else:
        return render(request, "events/delete.html", {"event": event})
