# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eighth', '0013_auto_20150523_1233'),
    ]

    operations = [
        migrations.AddField(
            model_name='eighthsponsor',
            name='show_full_name',
            field=models.BooleanField(default=False),
        ),
    ]
