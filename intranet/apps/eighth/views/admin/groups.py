# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six.moves import cPickle as pickle
import csv
import logging
from django import http
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from formtools.wizard.views import SessionWizardView
from ....auth.decorators import eighth_admin_required
from ....users.models import User
from ...forms.admin.activities import ActivitySelectionForm, ScheduledActivityMultiSelectForm
from ...forms.admin.blocks import BlockSelectionForm
from ...forms.admin.groups import QuickGroupForm, GroupForm, UploadGroupForm
from ...models import EighthScheduledActivity, EighthSignup, EighthBlock
from ...utils import get_start_date

logger = logging.getLogger(__name__)


@eighth_admin_required
def add_group_view(request):
    if request.method == "POST":
        form = QuickGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, "Successfully added group.")
            return redirect("eighth_admin_edit_group",
                            group_id=group.id)
        else:
            messages.error(request, "Error adding group.")
            try:
                request.session["add_group_form"] = pickle.dumps(form)
            except TypeError:
                """ Prevent pickle errors """
                pass
            return redirect("eighth_admin_dashboard")
    else:
        return http.HttpResponseNotAllowed(["POST"], "405: METHOD NOT ALLOWED")


@eighth_admin_required
def edit_group_view(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404

    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Successfully edited group.")
            return redirect("eighth_admin_dashboard")
        else:
            messages.error(request, "Error adding group.")
    else:
        form = GroupForm(instance=group)

    users = group.user_set.all()
    members = []
    for user in users:
        grade = user.grade
        emails = user.emails
        members.append({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "student_id": user.student_id,
            "email": emails[0] if emails else "",
            "grade": grade.number if user.grade else "Staff"
        })
    members = sorted(members, key=lambda m: (m["last_name"], m["first_name"]))
    context = {
        "group": group,
        "members": members,
        "edit_form": form,
        "admin_page_title": "Edit Group",
        "delete_url": reverse("eighth_admin_delete_group",
                              args=[group_id])
    }
    return render(request, "eighth/admin/edit_group.html", context)

def get_file_string(fileobj):
    filetext = ""
    for chunk in fileobj.chunks():
        filetext += chunk
    return filetext

def get_user_info(key, val):
    if key in ["username", "id"]:
        try:
            u = User.objects.filter(**{ key: val })
        except ValueError:
            return []
        return u

    if key == "student_id":
        u = User.objects.user_with_student_id(val)
        return [u] if u else []


def handle_group_input(filetext):
    logger.debug(filetext)
    sure_users = []
    unsure_users = []
    lines = filetext.splitlines()
    for line in lines:
        done = False
        line = line.strip()

        # Try username, user id
        for i in ["username", "id", "student_id"]:
            r = get_user_info(i, line)
            if r:
                sure_users.append([line, r[0]])
                done = True
                break

        if not done:
            unsure_users.append([line, r])

    logger.debug("Sure users:")
    logger.debug(sure_users)
    logger.debug("Unsure users:")
    logger.debug(unsure_users)

    return sure_users, unsure_users

@eighth_admin_required
def upload_group_members_view(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404
    stage = "upload"
    data = {}
    filetext = False
    if request.method == "POST":
        form = UploadGroupForm(request)
        logger.debug(request.FILES)
        if "file" in request.FILES:
            fileobj = request.FILES['file']
            filetext = get_file_string(fileobj)
        elif "filetext" in request.POST:
            filetext = request.POST.get("filetext")
        elif "user_id" in request.POST:
            userids = request.POST.getlist("user_id")
            num_added = 0
            bulk_users = []
            for uid in userids:
                user = User.objects.get(id=uid)
                if user is None:
                    messages.error(request, "User with ID {} does not exist".format(uid))
                else:
                    user.groups.add(group)
                    bulk_users.add(user)
                    num_added += 1
            User.objects.bulk_create(bulk_users)
            messages.success(request, "{} added to group {}".format(num_added, group))
            return redirect("eighth_admin_edit_group", group.id)


    else:
        form = UploadGroupForm()
    context = {
        "admin_page_title": "Upload Group Info",
        "form": form,
        "stage": stage,
        "data": data,
        "group": group
    }

    if filetext:
        context["stage"] = "parse"
        data = handle_group_input(filetext)
        context["sure_users"], context["unsure_users"] = data

    return render(request, "eighth/admin/upload_group.html", context)


@eighth_admin_required
def delete_group_view(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404

    if request.method == "POST":
        group.delete()
        messages.success(request, "Successfully deleted group.")
        return redirect("eighth_admin_dashboard")
    else:
        context = {
            "admin_page_title": "Delete Group",
            "item_name": str(group),
            "help_text": "Deleting this group will remove all records "
                         "of it related to eighth period."
        }

        return render(request, "eighth/admin/delete_form.html", context)


@eighth_admin_required
def download_group_csv_view(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404

    response = http.HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=\"{}\"".format(group.name)

    writer = csv.writer(response)
    writer.writerow(["Last Name", "First Name", "Student ID", "Grade", "Email"])

    for user in group.user_set.all():
        row = []
        row.append(user.last_name)
        row.append(user.first_name)
        row.append(user.student_id)
        grade = user.grade
        row.append(grade.number if grade else "Staff")
        emails = user.emails
        row.append(emails[0] if emails else None)
        writer.writerow(row)

    return response


class EighthAdminSignUpGroupWizard(SessionWizardView):
    FORMS = [
        ("block", BlockSelectionForm),
        ("activity", ActivitySelectionForm),
    ]

    TEMPLATES = {
        "block": "eighth/admin/sign_up_group.html",
        "activity": "eighth/admin/sign_up_group.html",
    }

    def get_template_names(self):
        return [self.TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step):
        kwargs = {}
        if step == "block":
            kwargs.update({
                "exclude_before_date": get_start_date(self.request)
            })
        if step == "activity":
            block = self.get_cleaned_data_for_step("block")["block"]
            kwargs.update({"block": block})

        labels = {
            "block": "Select a block",
            "activity": "Select an activity",
        }

        kwargs.update({"label": labels[step]})

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super(EighthAdminSignUpGroupWizard,
                        self).get_context_data(form=form, **kwargs)
        context.update({"admin_page_title": "Sign Up Group"})
        return context

    def done(self, form_list, **kwargs):
        block = form_list[0].cleaned_data["block"]
        activity = form_list[1].cleaned_data["activity"]
        scheduled_activity = EighthScheduledActivity.objects.get(
            block=block,
            activity=activity
        )

        try:
            group = Group.objects.get(id=kwargs["group_id"])
        except Group.DoesNotExist:
            raise http.Http404

        users = group.user_set.all()

        if not activity.both_blocks:
            EighthSignup.objects.filter(
                user__in=users,
                scheduled_activity__block=block
            ).delete()
            for user in users:
                EighthSignup.objects.create(
                    user=user,
                    scheduled_activity=scheduled_activity
                )
        else:
            EighthSignup.objects.filter(
                user__in=users,
                scheduled_activity__block__date=block.date
            )
            for user in users:
                all_sched_acts = EighthScheduledActivity.objects.filter(
                    block__date=block.date,
                    activity=activity
                )
                for sched_act in all_sched_acts:
                    EighthSignup.objects.create(
                        user=user,
                        scheduled_activity=sched_act
                    )

        messages.success(self.request, "Successfully signed up group for activity.")
        return redirect("eighth_admin_dashboard")

eighth_admin_signup_group = eighth_admin_required(
    EighthAdminSignUpGroupWizard.as_view(
        EighthAdminSignUpGroupWizard.FORMS
    )
)


class EighthAdminDistributeGroupWizard(SessionWizardView):
    FORMS = [
        ("block", BlockSelectionForm),
        ("activity", ScheduledActivityMultiSelectForm),
    ]

    TEMPLATES = {
        "block": "eighth/admin/distribute_group.html",
        "activity": "eighth/admin/distribute_group.html",
        "choose": "eighth/admin/distribute_group.html",
    }

    def get_template_names(self):
        return [self.TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step):
        kwargs = {}

        if step == "block":
            kwargs.update({
                "exclude_before_date": get_start_date(self.request)
            })
        if step == "activity":
            block = self.get_cleaned_data_for_step("block")["block"]
            kwargs.update({"block": block})

        labels = {
            "block": "Select a block",
            "activity": "Select multiple activities",
        }

        kwargs.update({"label": labels[step]})

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super(EighthAdminDistributeGroupWizard,
                        self).get_context_data(form=form, **kwargs)
        context.update({"admin_page_title": "Distribute Group Members Among Activities"})
        return context

    def done(self, form_list, **kwargs):
        block = form_list[0].cleaned_data["block"]
        activities = form_list[1].cleaned_data["activities"]

        logger.debug(block)
        logger.debug(activities)

        schact_ids = []
        for act in activities:
            try:
                schact = EighthScheduledActivity.objects.get(block=block, activity=act)
                schact_ids.append(schact.id)
            except EighthScheduledActivity.DoesNotExist:
                raise Http404

        args = ""
        for said in schact_ids:
            args += "&schact={}".format(said)

        if "group_id" in kwargs:
            gid = kwargs["group_id"]
            args += "&group={}".format(gid)
        
        if self.request.resolver_match.url_name == "eighth_admin_distribute_unsigned":
            args += "&unsigned=1&block={}".format(block.id)

        return redirect("/eighth/admin/groups/distribute_action?{}".format(args))

eighth_admin_distribute_group = eighth_admin_required(
    EighthAdminDistributeGroupWizard.as_view(
        EighthAdminDistributeGroupWizard.FORMS
    )
)

eighth_admin_distribute_unsigned = eighth_admin_required(
    EighthAdminDistributeGroupWizard.as_view(
        EighthAdminDistributeGroupWizard.FORMS
    )
)


@eighth_admin_required
def eighth_admin_distribute_action(request):
    if "users" in request.POST:
        logger.debug(request.POST)
        activity_user_map = {}
        for item in request.POST:
            if item[:6] == "schact":
                try:
                    sid = int(item[6:])
                    schact = EighthScheduledActivity.objects.get(id=sid)
                except EighthScheduledActivity.DoesNotExist:
                    messages.error(request, "ScheduledActivity does not exist with id {}".format(sid))

                userids = request.POST.getlist(item)
                activity_user_map[schact] = userids

        changes = 0
        logger.debug(activity_user_map)
        for schact, userids in activity_user_map.items():
            EighthSignup.objects.filter(
                user__id__in=userids,
                scheduled_activity__block=schact.block
            ).delete()
            for uid in userids:
                changes += 1
                EighthSignup.objects.create(
                    user=User.objects.get(id=int(uid)),
                    scheduled_activity=schact
                )

        messages.success(request, "Successfully signed up users for {} activities.".format(changes))

        return redirect("eighth_admin_dashboard")
    elif "schact" in request.GET:
        schactids = request.GET.getlist("schact")

        schacts = []
        for schact in schactids:
            try:
                sch = EighthScheduledActivity.objects.get(id=schact)
                schacts.append(sch)
            except EighthScheduledActivity.DoesNotExist:
                raise http.Http404

        users = []
        users_type = ""

        if "group" in request.GET:
            group = Group.objects.get(id=request.GET.get("group"))
            users = group.user_set.all()
            users_type = "group"
        elif "unsigned" in request.GET:
            unsigned = []

            if "block" in request.GET:
                blockid = request.GET.get("block")
                block = EighthBlock.objects.get(id=blockid)
            else:
                raise http.Http404

            students = User.objects.filter(username__startswith="2")
            for student in students:
                su = EighthSignup.objects.filter(user=student, scheduled_activity__block__id=blockid)
                if len(su) == 0:
                    unsigned.append(student)

            users = unsigned
            users_type = "unsigned"

        context = {
            "admin_page_title": "Distribute Group Members Across Activities",
            "users_type": users_type,
            "group": group if users_type == "group" else None,
            "eighthblock": block if users_type == "unsigned" else None,
            "schacts": schacts,
            "users": users,
            "show_selection": True
        }

        return render(request, "eighth/admin/distribute_group.html", context)
    else:
        return redirect("eighth_admin_dashboard")


@eighth_admin_required
def add_member_to_group_view(request, group_id):
    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"], "HTTP 405: METHOD NOT ALLOWED")

    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404

    next_url = reverse("eighth_admin_edit_group", kwargs={"group_id": group_id})

    if "student_id" not in request.POST or not request.POST["student_id"].isdigit():
        return redirect(next_url + "?error=s")

    student_id = request.POST["student_id"]
    user = User.objects.user_with_student_id(student_id)
    if user is None:
        return redirect(next_url + "?error=n")
    user.groups.add(group)
    user.save()
    messages.success(request, "Successfully added user \"{}\" to the group.".format(user.full_name))
    return redirect(next_url + "?added=" + str(student_id))


@eighth_admin_required
def remove_member_from_group_view(request, group_id, user_id):
    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"], "HTTP 405: METHOD NOT ALLOWED")

    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise http.Http404

    next_url = reverse("eighth_admin_edit_group", kwargs={"group_id": group_id})

    try:
        user = User.get_user(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "There was an error removing this user.")
        return redirect(next_url, status=400)

    group.user_set.remove(user)
    group.save()
    messages.success(request, "Successfully removed user \"{}\" from the group.".format(user.full_name))

    return redirect(next_url)
