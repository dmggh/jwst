# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ChannelModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_returned', models.DateTimeField(help_text=b'Datetime channel opened.', auto_now_add=True)),
                ('key', models.CharField(default=b'', help_text=b'Identifying key for channel.', max_length=128)),
            ],
            options={
                'db_table': 'jpoll_channel',
            },
        ),
        migrations.CreateModel(
            name='MessageModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('type', models.CharField(default=b'', help_text=b'type of message.', max_length=16)),
                ('json', models.TextField(default=b'', help_text=b'JSON contents of message.')),
                ('channel', models.ForeignKey(to='jpoll.ChannelModel')),
            ],
            options={
                'db_table': 'jpoll_message',
            },
        ),
    ]
