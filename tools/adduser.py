import sys

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

from crds import log

def adduser(user, email, password, super_user=False):
    try:
        user = User.objects.create_user(user, email, password)
    except IntegrityError:
        log.warning("User", repr(user), "already exists or other problem...")
        return

    # At this point, user is a User object that has already been saved
    # to the database. You can continue to change its attributes
    # if you want to change other fields.
    user.is_staff = True
    if super_user:
        user.is_superuser = True
    user.save()

if __name__ == "__main__":
    
    if "--super-user" in sys.argv:
        sys.argv.remove("--super-user")
        super_user = True
    else:
        super_user = False
        
    if len(sys.argv) != 4:
        print >>sys.stderr, "usage: adduser.py <username> <email> <password>"
        sys.exit(-1)
    else:
        adduser(*sys.argv[1:], super_user=super_user)

