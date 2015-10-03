# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six.moves.urllib import parse
from .base import *

"""In production, add a file called secret.py to the settings package that
defines SECRET_KEY and DATABASE_URL.

DATABASE_URL should be of the following form:
    postgres://<user>:<password>@<host>/<database>
"""

EMAIL_ANNOUNCEMENTS = True

DEBUG = os.getenv("DEBUG", "FALSE") == "TRUE"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SHOW_DEBUG_TOOLBAR = False

CACHES['default']['OPTIONS']['DB'] = 1

parse.uses_netloc.append("postgres")
url = parse.urlparse(DATABASE_URL)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname
    }
}

SHOW_DEBUG_TOOLBAR = os.getenv("SHOW_DEBUG_TOOLBAR", "YES") == "YES"


def debug_toolbar_callback(request):
    """Show the debug toolbar to those with the Django staff permission, excluding
       the Eighth Period office.
    """
    if request.is_ajax():
        return False

    if (hasattr(request, 'user') and
        request.user.is_authenticated()):
        return (request.user.is_staff and
                not request.user.id == 9999 and
                "debug" in request.GET)

    return False

if SHOW_DEBUG_TOOLBAR:
    DEBUG_TOOLBAR_CONFIG.update({
        "SHOW_TOOLBAR_CALLBACK": "intranet.settings.debug_toolbar_callback"
    })