import sys

from django.contrib.auth.models import User

def adduser(user, email, password):
    user = User.objects.create_user(user, email, password)

    # At this point, user is a User object that has already been saved
    # to the database. You can continue to change its attributes
    # if you want to change other fields.
    user.is_staff = True
    user.save()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print >>sys.stderr, "usage: adduser.py <username> <email> <password>"
        sys.exit(-1)
    else:
        adduser(*sys.argv[1:])

