"""Local integration tests: reuse connection credentials, isolate test data."""
from copy import deepcopy

from netbox.configuration import *

if "DATABASES" not in globals():
    DATABASES = {"default": deepcopy(DATABASE)}
else:
    DATABASES = deepcopy(DATABASES)
globals().pop("DATABASE", None)
DATABASES["default"]["TEST"] = {"NAME": "test_netbox_geoview"}
PLUGINS = ["netbox_geoview"]
PLUGINS_CONFIG = {"netbox_geoview": {}}
REDIS = deepcopy(REDIS)
REDIS["tasks"]["DATABASE"] = 14
REDIS["caching"]["DATABASE"] = 15
RQ = {"COMMIT_MODE": "auto"}
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DEBUG = False
DEFAULT_PERMISSIONS = {}
RELEASE_CHECK_URL = None
