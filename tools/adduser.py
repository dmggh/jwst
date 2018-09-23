import sys

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

from crds import log

def adduser(user, email, password, first_name="", last_name="", super_user=False, use_existing=False):
    try:
        if use_existing:
            log.info("Fetching existing user", user)
            user = User.objects.get(username=user)
        else:
            log.info("Creating new user", user)
            user = User.objects.create_user(user, email, password)
    except IntegrityError:
        log.warning("User", repr(user), "already exists or other problem...")
        return

    # At this point, user is a User object that has already been saved
    # to the database. You can continue to change its attributes
    # if you want to change other fields.
    user.is_staff = True
    if super_user:
        log.info("Setting superuser.")
        user.is_superuser = True
    user.set_password(password)
    user.first_name = first_name
    user.last_name = last_name
    user.save()

if __name__ == "__main__":
    
    if "--super-user" in sys.argv:
        sys.argv.remove("--super-user")
        super_user = True
    else:
        super_user = False

    if "--use-existing" in sys.argv:
        sys.argv.remove("--use-existing")
        use_existing = True
    else:
        use_existing = False
        
    if 4 <= len(sys.argv) <= 6:
        adduser(*sys.argv[1:], super_user=super_user, use_existing=use_existing)
    else:
        print("usage: adduser.py <username> <email> <password> [<first name> [<last name>]]", file=sys.stderr)
        sys.exit(-1)

