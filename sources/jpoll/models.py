"""Django database models to support the jpoll messaging system."""

from __future__ import print_function

import sys
import json

from django.db import models

# Create your models here.

class JpollError(Exception):
    """Some kind of error related to jpoll messaging."""

class ChannelModel(models.Model):
    """An ordered series of messages associated with a unique key."""
    class Meta:
        db_table = "jpoll_channel"

    last_returned = models.DateTimeField(auto_now_add=True, help_text="Datetime channel opened.")
    key = models.CharField(max_length=128, default="", help_text="Identifying key for channel.")

    # user = models.CharField(max_length=32, default="", help_text="Name of user who opened this channel.")
    @classmethod
    def new(cls, key):
        """Create a new channel with unique name `key`."""
        self = cls()
        self.key = key
        self.save()
        return self
    
    @classmethod
    def open(cls, key):
        """Reopen an existing channel."""
        try:
            channels = ChannelModel.objects.filter(key=key)
            if len(channels) > 1:
                raise JpollError("Duplicate channel model for '{}'".format(key))
            if len(channels) < 1:
                raise JpollError("Channel key '{}' not found.".format(key))
            return channels[0]
        except:
            for chan in ChannelModel.objects.filter(key=key):
                chan.wipe()
            return cls.new(key)
    
    def log(self, text):
        """Send a log message to the client."""
        self.push(["log_message", text])
        
#     def eval_js(self, js):
#         """Execute the specified javascript on the client."""
#         self.push(["eval_js", js])

    def push(self, message_obj):
        """Add a json encodable `message_obj` to this channel."""
        message = MessageModel()
        message.channel = self
        message.json = json.dumps(message_obj)
        message.save()
    
    def pull(self, since=None):
        """Return json for the list of messages pushed since datetime `since` or the last call if `since` is None."""
        if since is None:
            since = self.last_returned
        messages = MessageModel.objects.filter(channel=self, timestamp__gt=since)
        messages = list(messages.order_by("timestamp"))
        if messages:
            self.last_returned = messages[-1].timestamp
            self.save()
            return [msg.message for msg in messages]
        else:
            return []
    
    def wipe(self):
        """Remove this channel and all associated messages."""
        try:
            MessageModel.objects.filter(channel=self).delete()
        except Exception as exc:
            print("ERROR: Failed removing message objects for channel '{}'".format(self.key), 
                  file=sys.stderr)
        try:
            self.delete()
        except Exception as exc:
            print("ERROR: Failed removing channel object '{}'.".format(self.key), 
                  file=sys.stderr)
    
    @classmethod
    def wipe_key(cls, key):
        for chan in cls.objects.filter(key=key):
            chan.wipe()

class MessageModel(models.Model):
    """Model for a single jpoll message object,  one of an ordered series on a single channel."""
    class Meta:
        db_table = "jpoll_message"

    channel = models.ForeignKey(ChannelModel)
    timestamp = models.DateTimeField(auto_now_add=True)
    json = models.TextField(help_text  = "JSON contents of message.", default="")
    
    @property
    def message(self):
        return json.loads(self.json)
    
