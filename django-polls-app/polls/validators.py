from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


USERNAME_PROMPT = "Username (required, must be 5 characters e.g 'kg630'): "
USERNAME_EXISTS_MSG = (
    "pls use different username , a user with this username already exists"
)
USERNAME_LENGTH_MSG = "Username must be exactly 5 characters (e.g. 'kg630')."


def validate_username_value(username):
    if not username:
        raise ValidationError("Username is required.")
    if len(username) != 5:
        raise ValidationError(USERNAME_LENGTH_MSG)


def username_already_exists(username, database="default"):
    User = get_user_model()
    return (
        User._default_manager.db_manager(database)
        .filter(username=username)
        .exists()
    )
