# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0007_auto_20150606_2351'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='order',
            field=models.IntegerField(default=0),
        ),
    ]
