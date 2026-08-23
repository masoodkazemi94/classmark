#!/usr/bin/env python
import os
import sys


def main():
    settings_module = (
        "config.settings.test"
        if "test" in sys.argv
        else "config.settings.development"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
