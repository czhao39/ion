# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from django import http
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from intranet import settings
from ..auth.decorators import announcements_admin_required
from ..users.models import User
from .models import Announcement, AnnouncementRequest
from .forms import AnnouncementForm, AnnouncementRequestForm

logger = logging.getLogger(__name__)

def email_send(text_template, html_template, data, subject, emails, headers=None):
    """
        Send an HTML/Plaintext email with the following fields.

        text_template: URL to a Django template for the text email's contents
        html_template: URL to a Django tempalte for the HTML email's contents
        data: The context to pass to the templates
        subject: The subject of the email
        emails: The addresses to send the email to
        headers: A dict of additional headers to send to the message

    """

    text = get_template(text_template)
    html = get_template(html_template)
    text_content = text.render(data)
    html_content = html.render(data)
    subject = settings.EMAIL_SUBJECT_PREFIX + subject
    headers = {} if headers is None else headers
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_FROM, emails, headers=headers)
    msg.attach_alternative(html_content, "text/html")
    logger.debug(msg)
    msg.send()

    return msg


def request_announcement_email(request, form, obj):
    """
        Send an announcement request email

        form: The announcement request form
        obj: The announcement request object

    """

    logger.debug(form.data)
    teacher_ids = form.data["teachers_requested"]
    if type(teacher_ids) != list:
        teacher_ids = [teacher_ids]
    logger.debug(teacher_ids)
    teachers = User.objects.filter(id__in=teacher_ids)
    logger.debug(teachers)

    subject = "News Post Confirmation Request from {}".format(request.user.full_name)
    emails = []
    for teacher in teachers:
        emails.append(teacher.tj_email)
    logger.debug(emails)
    data = {
        "teachers": teachers,
        "user": request.user,
        "formdata": form.data,
        "info_link": reverse("approve_announcement", args=[obj.id])
    }
    email_send("announcements/emails/teacher_approve.txt", 
               "announcements/emails/teacher_approve.html",
               data, subject, emails)


def admin_request_announcement_email(request, form, obj):
    """
        Send an admin announcement request email

        form: The announcement request form
        obj: The announcement request object

    """

    subject = "News Post Approval Needed ({})".format(obj.title)
    emails = [settings.APPROVAL_EMAIL]
    data = {
        "req": obj,
        "formdata": form.data,
        "info_link": reverse("admin_approve_announcement", args=[obj.id])
    }
    email_send("announcements/emails/admin_approve.txt", 
               "announcements/emails/admin_approve.html",
               data, subject, emails)


@login_required
def request_announcement_view(request):
    """
        The request announcement page

    """
    if request.method == "POST":
        form = AnnouncementRequestForm(request.POST)
        logger.debug(form)
        logger.debug(form.data)
        if form.is_valid():
            obj = form.save(commit=True)
            obj.user = request.user
            obj.save()
            teacher_ids = form.data["teachers_requested"]
            # don't interpret as a character array
            if type(teacher_ids) != list:
                teacher_ids = [teacher_ids]
            logger.debug(teacher_ids)
            teachers = User.objects.filter(id__in=teacher_ids)

            ann = AnnouncementRequest.objects.get(id=obj.id)
            logger.debug(teachers)
            for teacher in teachers:
                ann.teachers_requested.add(teacher)
            ann.save()

            request_announcement_email(request, form, obj)
            messages.success(request, "Successfully added announcement request.")
            return redirect("index")
        else:
            messages.error(request, "Error adding announcement request")
    else:
        form = AnnouncementRequestForm()
    return render(request, "announcements/request.html", {"form": form, "action": "add"})

@login_required
def approve_announcement_view(request, req_id):
    """
        The approve announcement page.
        Teachers will be linked to this page from an email.

        req_id: The ID of the AnnouncementRequest

    """
    req = get_object_or_404(AnnouncementRequest, id=req_id)

    requested_teachers = req.teachers_requested.all()
    logger.debug(requested_teachers)
    if request.user not in requested_teachers:
        messages.error(request, "You do not have permission to approve this announcement.")
        return redirect("index")

    if request.method == "POST":
        form = AnnouncementRequestForm(request.POST, instance=req)
        if form.is_valid():
            obj = form.save(commit=True)
            if "approve" in request.POST:
                obj.teachers_approved.add(request.user)
                obj.save()
                if not obj.admin_email_sent:
                    admin_request_announcement_email(request, form, obj)
                    obj.admin_email_sent = True
                    obj.save()

                    messages.success(request, "Successfully approved announcement request. An Intranet administrator "
                                              "will review and post the announcement shortly. (Notification sent.)")
                else:
                    messages.success(request, "Successfully approved announcement request. An Intranet administrator "
                                              "will review and post the announcement shortly.")
            else:
                obj.save()
                messages.success(request, "You did not approve this request.")
                return redirect("index")
    
    form = AnnouncementRequestForm(instance=req)
    context = {
        "form": form,
        "req": req,
        "admin_approve": False
    }
    return render(request, "announcements/approve.html", context)

@announcements_admin_required
def admin_approve_announcement_view(request, req_id):
    """
        The administrator approval announcement request page.
        Admins will view this page through the UI.

        req_id: The ID of the AnnouncementRequest

    """
    req = get_object_or_404(AnnouncementRequest, id=req_id)

    requested_teachers = req.teachers_requested.all()
    logger.debug(requested_teachers)

    if request.method == "POST":
        form = AnnouncementRequestForm(request.POST, instance=req)
        if form.is_valid():
            req = form.save(commit=True)
            if "approve" in request.POST:
                groups = []
                if "groups" in request.POST:
                    group_ids = request.POST.getlist("groups")
                    groups = Group.objects.filter(id__in=group_ids)
                logger.debug(groups)
                announcement = Announcement.objects.create(title=req.title,
                                                           content=req.content,
                                                           author=req.author,
                                                           user=req.user,
                                                           expiration_date=req.expiration_date)
                for g in groups:
                    announcement.groups.add(g)
                announcement.save()

                req.posted = announcement
                req.posted_by = request.user
                req.save()
                messages.success(request, "Successfully approved announcement request. It has been posted.")
                return redirect("index")
            else:
                req.rejected = True
                req.posted_by = request.user
                req.save()
                messages.success(request, "You did not approve this request. It will be hidden.")
                return redirect("index")
    
    form = AnnouncementRequestForm(instance=req)
    all_groups = Group.objects.all()
    context = {
        "form": form,
        "req": req,
        "admin_approve": True,
        "all_groups": all_groups
    }
    return render(request, "announcements/approve.html", context)


@announcements_admin_required
def add_announcement_view(request):
    """
        Add an announcement

    """
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        logger.debug(form)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Successfully added announcement.")
            return redirect("index")
        else:
            messages.error(request, "Error adding announcement")
    else:
        form = AnnouncementForm()
    return render(request, "announcements/add_modify.html", {"form": form, "action": "add"})

@login_required
def view_announcement_view(request, id):
    """
        View an announcement

        id: announcement id

    """
    announcement = get_object_or_404(Announcement, id=id)

    return render(request, "announcements/view.html", {"announcement": announcement})

@announcements_admin_required
def modify_announcement_view(request, id=None):
    """
        Modify an announcement

        id: announcement id

    """
    if request.method == "POST":
        announcement = Announcement.objects.get(id=id)
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Successfully modified announcement.")
            return redirect("index")
        else:
            messages.error(request, "Error adding announcement")
    else:
        announcement = Announcement.objects.get(id=id)
        form = AnnouncementForm(instance=announcement)
    return render(request, "announcements/add_modify.html", {"form": form, "action": "modify", "id": id})


@announcements_admin_required
def delete_announcement_view(request, id):
    """
        Delete an announcement

        id: announcement id

    """
    if request.method == "POST":
        post_id = None
        try:
            post_id = request.POST["id"]
        except AttributeError:
            post_id = None
        try:
            Announcement.objects.get(id=post_id).delete()
            messages.success(request, "Successfully deleted announcement.")
        except Announcement.DoesNotExist:
            pass

        return redirect("index")
    else:
        announcement = get_object_or_404(Announcement, id=id)
        return render(request, "announcements/delete.html", {"announcement": announcement})

@login_required
def show_announcement_view(request):
    """
        Unhide an announcement that was hidden by the logged-in user.

        announcements_hidden in the user model is the related_name for
        "users_hidden" in the announcement model.
    """
    if request.method == "POST":
        announcement_id = request.POST.get("announcement_id")
        if announcement_id:
            announcement = Announcement.objects.get(id=announcement_id)
            announcement.user_map.users_hidden.remove(request.user)
            announcement.user_map.save()
            return http.HttpResponse("Unhidden")
        return http.Http404()
    else:
        return http.HttpResponseNotAllowed(["POST"], "405: METHOD NOT ALLOWED")

@login_required
def hide_announcement_view(request):
    """
        Hide an announcement for the logged-in user.

        announcements_hidden in the user model is the related_name for
        "users_hidden" in the announcement model.
    """
    if request.method == "POST":
        announcement_id = request.POST.get("announcement_id")
        if announcement_id:
            announcement = Announcement.objects.get(id=announcement_id)
            announcement.user_map.users_hidden.add(request.user)
            announcement.user_map.save()
            return http.HttpResponse("Hidden")
        return http.Http404()
    else:
        return http.HttpResponseNotAllowed(["POST"], "405: METHOD NOT ALLOWED")