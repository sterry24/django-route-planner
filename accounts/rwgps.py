"""RideWithGPS OAuth + API helpers.

Wraps the small slice of the RideWithGPS v1 API the app needs: the OAuth
authorization-code flow, listing the current user's routes, and fetching a
single route's track points. Endpoints and parameter names follow
https://ridewithgps.com/api/v1/doc.

Authentication
--------------
After a user completes the OAuth flow, their ``access_token`` is stored on
:class:`accounts.models.Profile`. API calls include ``Authorization: Bearer
<token>`` per the RWGPS auth docs.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings


class RWGPSError(Exception):
    """Raised on any RideWithGPS HTTP failure or unexpected response shape."""


def authorize_url(state: str) -> str:
    """Build the RWGPS authorization URL the user is redirected to.

    ``state`` is a CSRF-style nonce we round-trip through the redirect; the
    callback view verifies it matches the value we stashed in the session.
    """
    params = {
        'client_id': settings.RWGPS_CLIENT_ID,
        'redirect_uri': settings.RWGPS_REDIRECT_URI,
        'response_type': 'code',
        'state': state,
    }
    return f'{settings.RWGPS_AUTHORIZE_URL}?{urlencode(params)}'


def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Trade an authorization code for an access token.

    Returns the parsed JSON body, which contains at minimum ``access_token``
    and (typically) ``user`` info. Raises :class:`RWGPSError` on any HTTP or
    parse failure.
    """
    # Per OAuth 2.0 §2.3.1 the recommended way to authenticate the client at
    # the token endpoint is HTTP Basic with client_id:client_secret. RWGPS
    # rejects body-only credentials with an "invalid_client" error, so we
    # send Basic auth and keep only the grant material in the body.
    resp = requests.post(
        settings.RWGPS_TOKEN_URL,
        json={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.RWGPS_REDIRECT_URI,
        },
        auth=(settings.RWGPS_CLIENT_ID, settings.RWGPS_CLIENT_SECRET),
        timeout=15,
    )
    if resp.status_code >= 400:
        raise RWGPSError(f'Token exchange failed ({resp.status_code}): {resp.text[:200]}')
    try:
        return resp.json()
    except ValueError as exc:
        raise RWGPSError(f'Token response was not JSON: {exc}') from exc


def _api_get(token: str, path: str, **params) -> dict[str, Any]:
    """GET an authenticated RWGPS endpoint and return the parsed JSON.

    ``path`` is appended to ``settings.RWGPS_API_BASE_URL`` (no leading slash
    needed). Raises :class:`RWGPSError` on non-2xx responses.
    """
    url = f'{settings.RWGPS_API_BASE_URL}/{path.lstrip("/")}'
    resp = requests.get(
        url,
        headers={'Authorization': f'Bearer {token}'},
        params=params or None,
        timeout=20,
    )
    if resp.status_code >= 400:
        raise RWGPSError(f'RWGPS {path} returned {resp.status_code}: {resp.text[:200]}')
    try:
        return resp.json()
    except ValueError as exc:
        raise RWGPSError(f'RWGPS {path} response was not JSON: {exc}') from exc


def list_routes(token: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List the authenticated user's RWGPS routes (paginated).

    Returns the raw response, which has ``routes`` (list) and ``meta``
    (pagination info) keys per the RWGPS docs.
    """
    return _api_get(token, 'routes.json', page=page, page_size=page_size)


def fetch_route(token: str, route_id: int | str) -> dict[str, Any]:
    """Fetch a single RWGPS route, including its ``track_points`` array."""
    return _api_get(token, f'routes/{route_id}.json')


def track_points_to_coordinates(track_points: list[dict[str, Any]]) -> list[list[float]]:
    """Convert RWGPS ``track_points`` to our GeoJSON ``[lng, lat, ele?]`` form.

    RWGPS uses single-letter keys: ``x`` = longitude, ``y`` = latitude,
    ``e`` = elevation in metres. Elevation is omitted from the output when
    the point has no ``e`` value, matching how our other importers behave.
    """
    coords: list[list[float]] = []
    for tp in track_points:
        x = tp.get('x')
        y = tp.get('y')
        if x is None or y is None:
            continue
        c = [float(x), float(y)]
        e = tp.get('e')
        if e is not None:
            c.append(float(e))
        coords.append(c)
    return coords
