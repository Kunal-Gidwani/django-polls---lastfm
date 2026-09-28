import getpass

from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCommand,
)
from django.core import exceptions

from polls.validators import (
    USERNAME_EXISTS_MSG,
    USERNAME_PROMPT,
    username_already_exists,
    validate_username_value,
)


class Command(BaseCommand):
    def _get_input_message(self, field, default=None):
        if field is self.username_field:
            return USERNAME_PROMPT
        msg = super()._get_input_message(field, default)
        if field.name == "email":
            msg = msg.rstrip(": ") + " (optional): "
        return msg

    def _validate_username(self, username, verbose_field_name, database):
        if username_already_exists(username, database=database):
            return USERNAME_EXISTS_MSG
        try:
            validate_username_value(username)
        except exceptions.ValidationError as e:
            return "; ".join(e.messages)
        try:
            self.username_field.clean(username, None)
        except exceptions.ValidationError as e:
            return "; ".join(e.messages)
        return None

    def get_input_data(self, field, message, default=None):
        if field is self.username_field:
            raw_value = input(message)
            if raw_value == "":
                self.stderr.write("Error: Username is required.")
                return None
            try:
                validate_username_value(raw_value)
            except exceptions.ValidationError as e:
                self.stderr.write("Error: %s" % "; ".join(e.messages))
                return None
            try:
                return field.clean(raw_value, None)
            except exceptions.ValidationError as e:
                self.stderr.write("Error: %s" % "; ".join(e.messages))
                return None
        return super().get_input_data(field, message, default)

    def handle(self, *args, **options):
        original_getpass = getpass.getpass

        def patched_getpass(prompt="Password: ", stream=None):
            if prompt == "Password: ":
                prompt = "Password (required): "
            elif prompt == "Password (again): ":
                pass
            return original_getpass(prompt, stream)

        getpass.getpass = patched_getpass
        try:
            super().handle(*args, **options)
        finally:
            getpass.getpass = original_getpass
