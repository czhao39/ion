# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_remove_event_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2015, 6, 23, 16, 12, 26, 729553), auto_now=True),
            preserve_default=False,
        ),
    ]
