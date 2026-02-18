import json
import random
from .background_scroller.constants import SCROLLER_NAME_POOL, SCROLLER_DISPLAY_COUNT


def background_scroller_names(request):
    """
    Provides randomized background scroller names that persist for the session.
    Names are randomly selected once per session and remain consistent across page loads.
    Also provides the full name pool as JSON for JavaScript scramble animations.
    """
    session_key = 'scroller_names'

    if session_key not in request.session or len(request.session[session_key]) != SCROLLER_DISPLAY_COUNT:
        shuffled = random.sample(SCROLLER_NAME_POOL, len(SCROLLER_NAME_POOL))
        selected_names = [shuffled[i % len(shuffled)] for i in range(SCROLLER_DISPLAY_COUNT)]
        request.session[session_key] = selected_names

    return {
        'scroller_names': request.session[session_key],
        'scroller_name_pool_json': json.dumps(SCROLLER_NAME_POOL),
    }
