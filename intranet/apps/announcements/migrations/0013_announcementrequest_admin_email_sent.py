# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0012_auto_20150713_1348'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcementrequest',
            name='admin_email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
