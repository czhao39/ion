# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='receive_eighth_emails',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='receive_news_emails',
            field=models.BooleanField(default=False),
        ),
    ]
