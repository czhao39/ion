# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eighth', '0010_eighthscheduledactivity_admin_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='eighthsignup',
            name='absence_acknowledged',
            field=models.BooleanField(default=False),
        ),
    ]
