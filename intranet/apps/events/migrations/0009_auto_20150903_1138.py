# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_event_attending'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='announcement',
            field=models.ForeignKey(related_name='event', blank=True, to='announcements.Announcement', null=True),
        ),
    ]
