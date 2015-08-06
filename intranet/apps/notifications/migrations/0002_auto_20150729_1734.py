# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationconfig',
            name='android_gcm_token',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
    ]
