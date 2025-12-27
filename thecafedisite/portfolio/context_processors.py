import random
from .background_scroller.constants import SCROLLER_NAME_POOL, SCROLLER_DISPLAY_COUNT


def background_scroller_names(request):
    """
    Provides randomized background scroller names that persist for the session.
    Names are randomly selected once per session and remain consistent across page loads.
    """
    session_key = 'scroller_names'

    # Check if names already exist in session
    if session_key not in request.session:
        # First visit this session - randomly select names
        selected_names = random.sample(SCROLLER_NAME_POOL, SCROLLER_DISPLAY_COUNT)
        request.session[session_key] = selected_names

    return {
        'scroller_names': request.session[session_key]
    }
