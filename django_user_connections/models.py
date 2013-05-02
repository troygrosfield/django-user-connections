# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F

from django_tools.models import AbstractBaseModel
from python_tools.random_utils import random_alphanum_id

from .constants import Status
from .managers import ConnectionManager

User = get_user_model()


class Connection(AbstractBaseModel):
    """
    Fields:
    
    * status = status of the connection. Can be one of the following:
        accepted = the connection has been accepted
        pending = pending connection
    * token = token shared between the two users
    * user_ids  = list of user ids who are connected. This assumes that at most  
        2 people are connected.
    * email_sent = boolean indicating if a connection email was sent once
        a connection became accepted.
    * activity_count = the total number of interactions between two users.
    """

    status = models.CharField(max_length=25,
                              default=Status.PENDING,
                              choices=Status.CHOICES)
    users = models.ManyToManyField(User, db_index=True)
    token = models.CharField(max_length=50, db_index=True)
    email_sent = models.BooleanField(default=False)
    activity_count = models.IntegerField(default=1)
    objects = ConnectionManager()

    class Meta:
        ordering = ('-created_dttm',)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = Connection.get_next_token()

        return super(Connection, self).save(*args, **kwargs)

    def accept(self):
        """Accepts a user connection."""
        self.status = Status.ACCEPTED
        self.save()

    def decline(self):
        """Declines a user connection."""
        self.status = Status.DECLINED
        self.save()

    def increment_activity_count(self):
        """Increments total activity count for the connection between two users.
        """
        self.activity_count = F('activity_count') + 1
        self.save()
        return True

    @classmethod
    def increment_activity_count_by_users(cls, user_id_1, user_id_2):
        """Increments total activity count for the connection between two users.
        
        :param user_id_1: user id of the first user in a connection
        :param user_id_2: user id of the second user in a connection
        
        """
        return (cls.objects.filter(users__id=user_id_1)
                           .filter(users__id=user_id_2)
                           .update(activity_count=F('activity_count') + 1))

    def get_for_user_id(self):
        """Gets the user id this connection is intended for.  This is the user 
        that did NOT create the connection.
        
        """
        users = self.users.all()
        return users[1].id if users[0].id == self.created_id else users[0].id

    @classmethod
    def get_next_token(cls, length=20):
        """Gets the next available token.  This method ensures the token is 
        unique.
        
        """
        token = random_alphanum_id(length)
        while True:
            conn = cls.objects.get_by_token(token=token)
            if not conn:
                return token

            token = random_alphanum_id(length)
