# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0018_announcement_notify_post'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='announcement',
            options={'ordering': ['-added', '-pinned']},
        ),
        migrations.AddField(
            model_name='announcement',
            name='pinned',
            field=models.BooleanField(default=False),
        ),
    ]
