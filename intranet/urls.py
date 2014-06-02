from django.conf import settings
from django.conf.urls import patterns, url, include
import django.contrib.admin
from django.views.generic.base import RedirectView
from .apps.announcements import views as announcements
from .apps.auth import views as auth
from .apps.users import views as users
from .apps.eighth.views import activities, actsponsors, blocks, common, groups as eighth_groups, main, rooms, signup
from .apps.events import views as events
from .apps.files import views as files
from .apps.groups import views as groups
from .apps.polls import views as polls
from .apps.search import views as search

django.contrib.admin.autodiscover()

urlpatterns = patterns("",
    url(r"^favicon\.ico$", RedirectView.as_view(url="/static/img/favicon.ico"), name="favicon"),
    url(r"^api/", include("intranet.apps.api.urls"), name="api_root"),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
)

if settings.SHOW_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns += patterns("",
        url(r"^__debug__/", include(debug_toolbar.urls)),
    )

urlpatterns += patterns("auth.views.",
    url(r"^$", auth.index, name="index"),
    url(r"^login$", auth.login_view.as_view(), name="login"),
    url(r"^logout$", auth.logout_view, name="logout"),
)

urlpatterns += patterns("announcements.views.",
    url(r"^announcements/add$", announcements.add_announcement_view, name="add_announcement"),
    url(r"^announcements/modify/(?P<id>\d+)$", announcements.modify_announcement_view, name="modify_announcement"),
    url(r"^announcements/delete$", announcements.delete_announcement_view, name="delete_announcement"),
)

urlpatterns += patterns("eighth.views.",
    url(r"^eighth/?$", main.eighth_redirect_view, name="eighth_redirect"),
    url(r"^eighth/admin/?$", main.eighth_admin_view, name="eighth_admin"),
    url(r"^eighth/teacher/?$", main.eighth_teacher_view, name="eighth_teacher"),
# Choose
    url(r"^eighth/choose/block/?$", blocks.eighth_choose_block, name="eighth_choose_block"),
    url(r"^eighth/choose/activity(?:/block/(?P<block_id>\d+))?$", activities.eighth_choose_activity, name="eighth_choose_activity"),
    url(r"^eighth/choose/group/?$", eighth_groups.eighth_choose_group, name="eighth_choose_group"),
# Student
    url(r"^eighth/students/register/$", signup.eighth_students_register, name="eighth_students_register"),
    url(r"^eighth/students/register/(?P<match>.+)/$", signup.eighth_students_register, name="eighth_students_register"),

    url(r"^eighth/groups/$", eighth_groups.eighth_groups_edit, name="eighth_groups_edit"),
    url(r"^eighth/groups/edit/(?P<group_id>\d+)$", eighth_groups.eighth_groups_edit, name="eighth_groups_edit"),
# Activity
    url(r"^eighth/activities/$", activities.eighth_activities_edit, name="eighth_activities_edit"),
    url(r"^eighth/activities/add/$", activities.eighth_activities_add, name="eighth_activities_add"),
    url(r"^eighth/activities/view/$", activities.eighth_activities_edit, name="eighth_activities_edit"),
    url(r"^eighth/activities/edit/$", activities.eighth_activities_edit, name="eighth_activities_edit"),
    url(r"^eighth/activities/edit/(?P<activity_id>\d+)$", activities.eighth_activities_edit, name="eighth_activities_edit"),
    url(r"^eighth/activities/delete/(?P<activity_id>\d+)$", activities.eighth_activities_delete, name="eighth_activities_delete"),

    url(r"^eighth/activities/schedule/$", activities.eighth_activities_schedule, name="eighth_activities_schedule"),
    url(r"^eighth/activities/schedule/form/$", activities.eighth_activities_schedule_form, name="eighth_activities_schedule_form"),
    url(r"^eighth/activities/schedule/(?P<match>.+)/$", activities.eighth_activities_schedule, name="eighth_activities_schedule"),

    url(r"^eighth/activities/sponsors/$", actsponsors.eighth_activities_sponsors_edit, name="eighth_activities_sponsors_edit"),
    url(r"^eighth/activities/sponsors/add/$", actsponsors.eighth_activities_sponsors_add, name="eighth_activities_sponsors_add"),
    url(r"^eighth/activities/sponsors/view/$", actsponsors.eighth_activities_sponsors_edit, name="eighth_activities_sponsors_edit"),
    url(r"^eighth/activities/sponsors/edit/$", actsponsors.eighth_activities_sponsors_edit, name="eighth_activities_sponsors_edit"),
    url(r"^eighth/activities/sponsors/edit/(?P<sponsor_id>\d+)$", actsponsors.eighth_activities_sponsors_edit, name="eighth_activities_sponsors_edit"),
    url(r"^eighth/activities/sponsors/delete/(?P<sponsor_id>\d+)$", actsponsors.eighth_activities_sponsors_delete, name="eighth_activities_sponsors_delete"),

    url(r"^eighth/rooms/$", rooms.eighth_rooms_edit, name="eighth_rooms_edit"),
    url(r"^eighth/rooms/add/$", rooms.eighth_rooms_add, name="eighth_rooms_add"),
    url(r"^eighth/rooms/view/$", rooms.eighth_rooms_edit, name="eighth_rooms_edit"),
    url(r"^eighth/rooms/edit/$", rooms.eighth_rooms_edit, name="eighth_rooms_edit"),
    url(r"^eighth/rooms/edit/(?P<room_id>\d+)$", rooms.eighth_rooms_edit, name="eighth_rooms_edit"),
    url(r"^eighth/rooms/delete/(?P<room_id>\d+)$", rooms.eighth_rooms_delete, name="eighth_rooms_delete"),

#Special
    url(r"^eighth/blocks/$", blocks.eighth_blocks_edit, name="eighth_blocks_edit"),
    url(r"^eighth/blocks/add/$", blocks.eighth_blocks_add, name="eighth_blocks_add"),
    url(r"^eighth/blocks/view/$", blocks.eighth_blocks_edit, name="eighth_blocks_edit"),
    url(r"^eighth/blocks/edit/$", blocks.eighth_blocks_edit, name="eighth_blocks_edit"),
    url(r"^eighth/blocks/edit/(?P<block_id>\d+)$", blocks.eighth_blocks_edit, name="eighth_blocks_edit"),
    url(r"^eighth/blocks/delete/(?P<block_id>\d+)$", blocks.eighth_blocks_delete, name="eighth_blocks_delete"),

    url(r"^eighth/startdate/$", common.eighth_startdate, name="eighth_startdate"),

    url(r"^eighth/signup(?:/block/(?P<block_id>\d+))?$", signup.eighth_signup_view, name="eighth_signup"),
)

urlpatterns += patterns("events.views.",
    url(r"^events$", events.events_view, name="events"),
)

urlpatterns += patterns("files.views.",
    url(r"^files$", files.files_view, name="files"),
)

urlpatterns += patterns("groups.views.",
    url(r"^groups$", groups.groups_view, name="groups"),
	url(r"^groups/add$", groups.add_group_view, name="add_groups"),
)

urlpatterns += patterns("polls.views.",
    url(r"^polls$", polls.polls_view, name="polls"),
)

urlpatterns += patterns("users.views.",
    url(r"^profile(?:/(?P<user_id>\d+))?$", users.profile_view, name="user_profile"),
    url(r"^picture/(?P<user_id>\d+)(?:/(?P<year>freshman|sophomore|junior|senior))?$", users.picture_view, name="profile_picture")
)

urlpatterns += patterns("search.views.",
    url(r"^search$", search.search_view, name="search"),
)

urlpatterns += [
    url(r'^djangoadmin/', include(django.contrib.admin.site.urls)),
]
