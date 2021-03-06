# -*- coding: utf-8 -*-

import logging

from django.db import models

from ..search.views import get_search_results
from ..users.models import User

logger = logging.getLogger(__name__)


class LDAPCourse(models.Model):
    users = models.ManyToManyField(User)

    course_id = models.CharField(max_length=10, blank=False, unique=False)
    section_id = models.CharField(max_length=10, blank=False, unique=True)

    course_title = models.CharField(max_length=100, blank=True)
    course_short_title = models.CharField(max_length=100, blank=True)
    teacher_name = models.CharField(max_length=100, blank=True)
    room_name = models.CharField(max_length=100, blank=True)
    term_code = models.CharField(max_length=10, blank=True)
    period = models.IntegerField()
    end_period = models.IntegerField()

    def teacher_user(self):
        query = self.teacher_name.replace(",", "")  # Remove comma between last and first
        query = " ".join(query.split(" ")[:2])  # Remove middle initial
        try:
            query_error, users = get_search_results(query, False)
        except Exception:
            return None

        logger.debug("user find result: {}".format(users))

        if users and len(users) == 1:
            return users[0]

    def __str__(self):
        return "{} - {} ({})".format(self.course_title, self.teacher_name, self.section_id)
