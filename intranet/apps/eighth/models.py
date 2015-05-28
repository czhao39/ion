
from __future__ import unicode_literals

from itertools import chain
import logging
import datetime
from django.db import models
from django.db.models import Manager, Q
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.utils import formats
from ..users.models import User
from . import exceptions as eighth_exceptions

logger = logging.getLogger(__name__)


class AbstractBaseEighthModel(models.Model):
    created_time = models.DateTimeField(auto_now_add=True, null=True)
    last_modified_time = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class EighthSponsor(AbstractBaseEighthModel):

    """Represents a sponsor for an eighth period activity.

    A sponsor could be linked to an actual user or just a name.

    Attributes:
        first_name
            The first name of the sponsor
        last_name
            The last name of the sponsor
        user
            A :class:`User<intranet.apps.users.models.User>` object
            linked to the sponsor.
        online_attendance
            Whether the sponsor takes attendance online.
        show_full_name
            Whether to always show the sponsor's full name
            (e.x. because there are two teachers named Lewis)
    """

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    user = models.OneToOneField(User, null=True, blank=True)
    online_attendance = models.BooleanField(default=True)
    show_full_name = models.BooleanField(default=False)

    class Meta:
        unique_together = (("first_name",
                            "last_name",
                            "user",
                            "online_attendance"),)
        ordering = ("last_name", "first_name",)

    def __unicode__(self):
        return self.first_name + " " + self.last_name

    @property
    def name(self):
        if self.show_full_name:
            return self.first_name + " " + self.last_name
        else:
            return self.last_name


class EighthRoom(AbstractBaseEighthModel):

    """Represents a room in which an eighth period activity can be held

    Attributes:
        name
            The name of the room.
        capacity
            The maximum capacity of the room (-1 for unlimited, 0 to prevent student signup)

    """
    name = models.CharField(max_length=100)
    capacity = models.SmallIntegerField(default=28)

    unique_together = (("name", "capacity"),)

    @classmethod
    def total_capacity_of_rooms(cls, rooms):
        capacity = 0
        for r in rooms:
            c = r.capacity
            if c == -1:
                return -1
            else:
                capacity += c
        return capacity

    def __unicode__(self):
        return "{} ({})".format(self.name, self.capacity)

    class Meta:
        ordering = ("name",)


class EighthActivityExcludeDeletedManager(models.Manager):

    def get_query_set(self):
        return (super(EighthActivityExcludeDeletedManager, self).get_query_set()
                                                                .exclude(deleted=True))


class EighthActivity(AbstractBaseEighthModel):

    """Represents an eighth period activity.

    Attributes:
        name
            The name of the activity.
        sponsors
            The :class:`EighthSponsor`\s for the activity.

    """
    objects = models.Manager()
    undeleted_objects = EighthActivityExcludeDeletedManager()

    name = models.CharField(max_length=100)  # This should really be unique
    description = models.CharField(max_length=2000, blank=True)
    sponsors = models.ManyToManyField(EighthSponsor, blank=True)
    rooms = models.ManyToManyField(EighthRoom, blank=True)

    presign = models.BooleanField(default=False)
    one_a_day = models.BooleanField(default=False)
    both_blocks = models.BooleanField(default=False)
    sticky = models.BooleanField(default=False)
    special = models.BooleanField(default=False)
    administrative = models.BooleanField(default=False)

    restricted = models.BooleanField(default=False)

    users_allowed = models.ManyToManyField(User,
                                           related_name="restricted_activity_set",
                                           blank=True)
    groups_allowed = models.ManyToManyField(Group,
                                            related_name="restricted_activity_set",
                                            blank=True)

    freshmen_allowed = models.BooleanField(default=False)
    sophomores_allowed = models.BooleanField(default=False)
    juniors_allowed = models.BooleanField(default=False)
    seniors_allowed = models.BooleanField(default=False)

    favorites = models.ManyToManyField(User,
                                       related_name="favorited_activity_set",
                                       blank=True)

    deleted = models.BooleanField(blank=True, default=False)

    def capacity(self):
        # Note that this is the default capacity if the
        # rooms/capacityare not overridden for a particular block.

        rooms = self.rooms.all()
        return EighthRoom.total_capacity_of_rooms(rooms)

    @property
    def name_with_flags(self):
        return self._name_with_flags(True)

    @property
    def name_with_flags_no_restricted(self):
        return self._name_with_flags(False)

    def _name_with_flags(self, include_restricted):
        name = "Special: " if self.special else ""
        name += self.name
        if include_restricted:
            name += " (R)" if self.restricted else ""
        name += " (BB)" if self.both_blocks else ""
        name += " (A)" if self.administrative else ""
        name += " (S)" if self.sticky else ""
        name += " (Deleted)" if self.deleted else ""
        return name

    @classmethod
    def restricted_activities_available_to_user(cls, user):
        activities = set(user.restricted_activity_set
                             .values_list("id", flat=True))

        grade = user.grade.number

        if grade == 9:
            activities |= set(EighthActivity.objects
                                            .filter(freshmen_allowed=True)
                                            .values_list("id", flat=True))
        elif grade == 10:
            activities |= set(EighthActivity.objects
                                            .filter(sophomores_allowed=True)
                                            .values_list("id", flat=True))
        elif grade == 11:
            activities |= set(EighthActivity.objects
                                            .filter(juniors_allowed=True)
                                            .values_list("id", flat=True))
        elif grade == 12:
            activities |= set(EighthActivity.objects
                                            .filter(seniors_allowed=True)
                                            .values_list("id", flat=True))

        for group in user.groups.all():
            activities |= set(group.restricted_activity_set
                                   .values_list("id", flat=True))

        return list(activities)

    class Meta:
        verbose_name_plural = "eighth activities"

    def __unicode__(self):
        return self.name_with_flags


class EighthBlockManager(models.Manager):

    def get_first_upcoming_block(self):
        """Gets the first upcoming block (the first block that will
        take place in the future). If there is no block in the future,
        the most recent block will be returned

        Returns: the `EighthBlock` object

        """

        now = datetime.datetime.now()

        # Show same day if it's before 17:00
        if now.hour < 17:
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)

        block = self.order_by("date", "block_letter").filter(date__gte=now).first()
        return block

    def get_current_blocks(self):
        try:
            first_upcoming_block = self.get_first_upcoming_block()
            if first_upcoming_block is None:
                raise EighthBlock.DoesNotExist()
            block = (self.prefetch_related("eighthscheduledactivity_set")
                         .get(id=first_upcoming_block.id))
        except EighthBlock.DoesNotExist:
            return []

        return block.get_surrounding_blocks()


class EighthBlock(AbstractBaseEighthModel):

    """Represents an eighth period block.

    Attributes:
        date
            The date of the block.
        block_letter
            The block letter (e.g. A, B).
        locked
            Whether signups are closed.
        activities
            List of :class:`EighthScheduledActivity`\s for the block.

    """

    objects = EighthBlockManager()

    date = models.DateField(null=False)
    block_letter = models.CharField(max_length=1)
    locked = models.BooleanField(default=False)
    activities = models.ManyToManyField(EighthActivity,
                                        through="EighthScheduledActivity",
                                        blank=True)

    def save(self, *args, **kwargs):
        letter = getattr(self, "block_letter", None)
        if letter:
            self.block_letter = letter.capitalize()

        super(EighthBlock, self).save(*args, **kwargs)

    def next_blocks(self, quantity=-1):
        blocks = (EighthBlock.objects
                             .order_by("date", "block_letter")
                             .filter(Q(date__gt=self.date)
                                     | (Q(date=self.date)
                                        & Q(block_letter__gt=self.block_letter))
                                     ))
        if quantity == -1:
            return blocks
        return blocks[:quantity + 1]

    def previous_blocks(self, quantity=-1):
        blocks = (EighthBlock.objects
                             .order_by("-date", "-block_letter")
                             .filter(Q(date__lt=self.date)
                                     | (Q(date=self.date)
                                        & Q(block_letter__lt=self.block_letter))
                                     ))
        if quantity == -1:
            return reversed(blocks)
        return reversed(blocks[:quantity + 1])

    def get_surrounding_blocks(self):
        """Get the blocks around the one given.
           Returns: a list of all of those blocks."""

        next = self.next_blocks()
        prev = self.previous_blocks()

        surrounding_blocks = list(chain(prev, [self], next))
        return surrounding_blocks

    def is_today(self):
        """Does the block occur today?"""
        return datetime.date.today() == self.date

    def __unicode__(self):
        formatted_date = formats.date_format(self.date, "EIGHTH_BLOCK_DATE_FORMAT")
        return "{} ({})".format(formatted_date, self.block_letter)

    class Meta:
        unique_together = (("date", "block_letter"),)
        ordering = ("date", "block_letter")


class EighthScheduledActivityManager(Manager):
    """Model Manager for EighthScheduledActivity"""

    def for_sponsor(cls, sponsor):
        """Return a QueryList of EighthScheduledActivities where the given
        EighthSponsor is sponsoring.

        If a sponsorship is defined in an EighthActivity, it may be overridden
        on a block by block basis in an EighthScheduledActivity. Sponsors from
        the EighthActivity do not carry over.

        EighthScheduledActivities that are deleted or cancelled are also not
        counted.

        """
        sponsoring_filter = (Q(sponsors=sponsor) |
                             (Q(sponsors=None) & Q(activity__sponsors=sponsor)))
        sched_acts = (EighthScheduledActivity.objects
                                             .exclude(activity__deleted=True)
                                             .exclude(cancelled=True)
                                             .filter(sponsoring_filter))
        return sched_acts


class EighthScheduledActivity(AbstractBaseEighthModel):

    """Represents the relationship between an activity and a block in
    which it has been scheduled.

    Attributes:
        block : :class:`EighthBlock`
            The :class:`EighthBlock` during which an
            :class:`EighthActivity` has been scheduled
        activity
            The scheduled :class:`EighthActivity`
        members
            The :class:`User<intranet.apps.users.models.User>`\s who have
            signed up for an :class:`EighthBlock`
        comments
            Notes for students
        admin_comments
            Notes for the Eighth Office
        sponsors
            :class:`EighthSponsor`\s that will override the
            :class:`EighthActivity`'s default sponsors
        rooms
            :class:`EighthRoom`\s that will override the
            :class:`EighthActivity`'s default rooms
        attendance_taken
            whether the :class:`EighthSponsor` for the scheduled
            :class:`EighthActivity` has taken attendance yet
        cancelled
            whether the :class:`EighthScheduledActivity` has been cancelled

    """

    # Use model manager
    objects = EighthScheduledActivityManager()

    block = models.ForeignKey(EighthBlock)
    activity = models.ForeignKey(EighthActivity)
    members = models.ManyToManyField(
        User,
        through="EighthSignup",
        related_name="eighthscheduledactivity_set"
    )

    admin_comments = models.CharField(max_length=1000, blank=True)
    comments = models.CharField(max_length=1000, blank=True)

    # Overridden attributes
    sponsors = models.ManyToManyField(EighthSponsor, blank=True)
    rooms = models.ManyToManyField(EighthRoom, blank=True)
    capacity = models.SmallIntegerField(null=True, blank=True)

    attendance_taken = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)

    def get_true_sponsors(self):
        """Get the sponsors for the scheduled activity, taking into account
        activity defaults and overrides.
        """

        sponsors = self.sponsors.all()
        if len(sponsors) > 0:
            return sponsors
        else:
            return self.activity.sponsors.all()

    def user_is_sponsor(self, user):
        """Return whether the given user is a sponsor of the activity.

        Returns:
            Boolean
        """
        sponsors = self.get_true_sponsors()
        for sponsor in sponsors:
            sp_user = sponsor.user
            if sp_user == user:
                return True

        return False

    def get_true_rooms(self):
        """Get the rooms for the scheduled activity, taking into account
        activity defaults and overrides.

        """

        rooms = self.rooms.all()
        if len(rooms) > 0:
            return rooms
        else:
            return self.activity.rooms.all()

    def get_true_capacity(self):
        """Get the capacity for the scheduled activity, taking into
        account activity defaults and overrides.

        """

        c = self.capacity
        if c is not None:
            return c
        else:
            rooms = self.get_true_rooms()
            return EighthRoom.total_capacity_of_rooms(rooms)

    def is_full(self):
        capacity = self.get_true_capacity()
        if capacity != -1:
            num_signed_up = self.eighthsignup_set.count()
            return num_signed_up >= capacity
        return False

    def is_overbooked(self):
        capacity = self.get_true_capacity()
        if capacity != -1:
            num_signed_up = self.eighthsignup_set.count()
            return num_signed_up > capacity
        return False

    def is_too_early_to_signup(self, now=None):
        if now is None:
            now = datetime.datetime.now()

        activity_date = (datetime.datetime
                                 .combine(self.block.date,
                                          datetime.time(0, 0, 0)))
        presign_period = datetime.timedelta(days=2)

        return (now < (activity_date - presign_period))

    def add_user(self, user, request=None, force=False):
        """Sign up a user to this scheduled activity if possible.

        Raises an exception if there's a problem signing the user up
        unless the signup is forced.

        """

        if request is not None:
            force = force or (("force" in request.GET) and
                              request.user.is_eighth_admin)
        exception = eighth_exceptions.SignupException()

        if not force:
            # Check if the user who sent the request has the permissions
            # to change the target user's signups
            if request is not None:
                if user != request.user and not request.user.is_eighth_admin:
                    exception.SignupForbidden = True
                    raise exception

            if self.activity.both_blocks:
                # Find all schedulings of the same activity on the same day
                all_sched_act = (EighthScheduledActivity.objects
                                                        .filter(block__date=self.block.date,
                                                                activity=self.activity))
            else:
                all_sched_act = [self]

            # Check if the block has been locked
            for sched_act in all_sched_act:
                if sched_act.block.locked:
                    exception.BlockLocked = True

            # Check if the scheduled activity has been cancelled
            for sched_act in all_sched_act:
                if sched_act.cancelled:
                    exception.ScheduledActivityCancelled = True

            # Check if the activity has been deleted
            if self.activity.deleted:
                exception.ActivityDeleted = True

            # Check if the activity is full
            for sched_act in all_sched_act:
                if sched_act.is_full():
                    exception.ActivityFull = True

            # Check if it's too early to sign up for the activity
            if self.activity.presign:
                if self.is_too_early_to_signup():
                    exception.Presign = True

            # Check if the user is already stickied into an activity
            if not self.activity.both_blocks:
                in_stickie = (EighthSignup.objects
                                          .filter(user=user,
                                                  scheduled_activity__activity__sticky=True,
                                                  scheduled_activity__block=self.block)
                                          .exists())
            else:
                in_stickie = (EighthSignup.objects
                                          .filter(user=user,
                                                  scheduled_activity__activity__sticky=True,
                                                  scheduled_activity__block__date=self.block.date,
                                                  scheduled_activity__activity=self.activity)
                                          .exists())
            if in_stickie:
                exception.Sticky = True

            # Check if signup would violate one-a-day constraint
            if not self.activity.both_blocks and self.activity.one_a_day:
                in_act = (EighthSignup.objects
                                      .exclude(scheduled_activity__block=self.block)
                                      .filter(user=user,
                                              scheduled_activity__block__date=self.block.date,
                                              scheduled_activity__activity=self.activity)
                                      .exists())
                if in_act:
                    exception.OneADay = True

            # Check if user is allowed in the activity if it's restricted
            if self.activity.restricted:
                acts = EighthActivity.restricted_activities_available_to_user(user)
                if self.activity.id not in acts:
                    exception.Restricted = True

        # If we've collected any errors, raise the exception and abort
        # the signup attempt
        if exception.errors:
            raise exception

        # Everything's good to go - complete the signup. If we've gotten to
        # this point, the signup is either before deadline or performed by
        # an eighth period admin, so previous absences and passes are cleared.
        after_deadline = self.block.locked
        if not self.activity.both_blocks:
            try:
                existing_signup = (EighthSignup.objects
                                               .get(user=user,
                                                    scheduled_activity__block=self.block))

                previous_activity_name = existing_signup.scheduled_activity.activity.name_with_flags
                prev_sponsors = existing_signup.scheduled_activity.get_true_sponsors()
                previous_activity_sponsors = ", ".join(map(str, prev_sponsors))

                if not existing_signup.scheduled_activity.activity.both_blocks:
                    existing_signup.scheduled_activity = self
                    existing_signup.after_deadline = after_deadline
                    existing_signup.was_absent = False
                    existing_signup.absence_acknowledged = False
                    existing_signup.pass_accepted = False
                    existing_signup.previous_activity_name = previous_activity_name
                    existing_signup.previous_activity_sponsors = previous_activity_sponsors
                    existing_signup.save()
                else:
                    # Clear out the other signups for this block if the user is
                    # switching out of a both-blocks activity
                    EighthSignup.objects.filter(
                        user=user,
                        scheduled_activity__block__date=self.block.date
                    ).delete()
                    EighthSignup.objects.create(user=user,
                                                scheduled_activity=self,
                                                after_deadline=after_deadline,
                                                previous_activity_name=previous_activity_name,
                                                previous_activity_sponsors=previous_activity_sponsors)
            except EighthSignup.DoesNotExist:
                EighthSignup.objects.create(user=user,
                                            scheduled_activity=self,
                                            after_deadline=after_deadline)
        else:

            all_sched_act = (EighthScheduledActivity.objects
                                                    .filter(block__date=self.block.date,
                                                            activity=self.activity))

            existing_signups = EighthSignup.objects.filter(
                user=user,
                scheduled_activity__block__date=self.block.date
            )

            prev_data = {}
            for signup in existing_signups:
                prev_sponsors = signup.scheduled_activity.get_true_sponsors()
                prev_data[signup.scheduled_activity.block.block_letter] = {
                    "name": signup.scheduled_activity.activity.name_with_flags,
                    "sponsors": ", ".join(map(str, prev_sponsors))
                }
            existing_signups.delete()

            for sched_act in all_sched_act:
                letter = sched_act.block.block_letter
                if letter in prev_data:
                    previous_activity_name = prev_data[letter]["name"]
                    previous_activity_sponsors = prev_data[letter]["sponsors"]
                else:
                    previous_activity_name = None
                    previous_activity_sponsors = None

                EighthSignup.objects.create(user=user,
                                            scheduled_activity=sched_act,
                                            after_deadline=after_deadline,
                                            previous_activity_name=previous_activity_name,
                                            previous_activity_sponsors=previous_activity_sponsors)

                # signup.previous_activity_name = signup.activity.name_with_flags
                # signup.previous_activity_sponsors = ", ".join(map(str, signup.get_true_sponsors()))

    class Meta:
        unique_together = (("block", "activity"),)
        verbose_name_plural = "eighth scheduled activities"

    def __unicode__(self):
        cancelled_str = " (Cancelled)" if self.cancelled else ""
        return "{} on {}{}".format(self.activity, self.block, cancelled_str)


class EighthSignup(AbstractBaseEighthModel):

    """Represents a signup/membership in an eighth period activity.

    Attributes:
        user
            The :class:`User<intranet.apps.users.models.User>` who has
            signed up.
        scheduled_activity
            The :class:`EighthScheduledActivity` for which the user
            has signed up.
        after_deadline
            Whether the signup was after deadline.
        previous_activity_name
            The name of the activity the student was previously signed
            up for (used for passes)
        previous_activity_sponsors
            The sponsors of the activity the student was previously
            signed up for.
        pass_accepted
            Whether the pass was accepted
        was_absent
            Whether the student was absent.
        absence_acknowledged
            Whether the student has dismissed the absence notification.

    """
    time = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(User, null=False)
    scheduled_activity = models.ForeignKey(
        EighthScheduledActivity,
        related_name="eighthsignup_set",
        null=False,
        db_index=True
    )

    # An after-deadline signup is assumed to be a pass
    after_deadline = models.BooleanField(default=False)
    previous_activity_name = models.CharField(max_length=200, blank=True, null=True, default=None)
    previous_activity_sponsors = models.CharField(max_length=10000, blank=True, null=True, default=None)

    pass_accepted = models.BooleanField(default=False, blank=True)
    was_absent = models.BooleanField(default=False, blank=True)
    absence_acknowledged = models.BooleanField(default=False, blank=True)

    def validate_unique(self, *args, **kwargs):
        super(EighthSignup, self).validate_unique(*args, **kwargs)

        not_unique = (self.__class__
                          .objects
                          .exclude(pk=self.pk)
                          .filter(user=self.user,
                                  scheduled_activity__block=self.scheduled_activity.block)
                          .exists())

        if not_unique:
            raise ValidationError({
                NON_FIELD_ERRORS: ("EighthSignup already exists for the User "
                                   "and the EighthScheduledActivity's block",)
            })

    def __unicode__(self):
        return "{}: {}".format(self.user,
                               self.scheduled_activity)

    class Meta:
        unique_together = (("user", "scheduled_activity"),)
