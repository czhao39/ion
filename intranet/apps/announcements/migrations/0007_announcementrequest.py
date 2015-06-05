# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('announcements', '0006_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnouncementRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=127)),
                ('content', models.TextField()),
                ('notes', models.TextField()),
                ('added', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('posted', models.ForeignKey(blank=True, to='announcements.Announcement', null=True)),
                ('teachers_approved', models.ManyToManyField(related_name='teachers_approved', to=settings.AUTH_USER_MODEL, blank=True)),
                ('teachers_requested', models.ManyToManyField(related_name='teachers_requested', to=settings.AUTH_USER_MODEL, blank=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['-added'],
            },
        ),
    ]
