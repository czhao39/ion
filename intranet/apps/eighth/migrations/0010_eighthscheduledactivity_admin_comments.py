# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eighth', '0009_eighthactivity_favorites'),
    ]

    operations = [
        migrations.AddField(
            model_name='eighthscheduledactivity',
            name='admin_comments',
            field=models.CharField(max_length=1000, blank=True),
        ),
    ]
