"""AutoCold app package."""
import warnings

# ponytail: silence requests' version-mismatch noise; real errors still raise.
# Message filter first: importing requests emits the warning before the class exists to filter on.
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
try:
    from requests.exceptions import RequestsDependencyWarning
    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    pass
