User guide
==========

Sign up and sign in
-------------------

Visit ``/accounts/signup/`` to create an account. Username, email, and
password are required. After signup you are logged in automatically and
redirected to the route list.

Existing users sign in at ``/accounts/login/``. Logging out is a single
click in the navigation bar.

Pick units
----------

Open ``/accounts/settings/`` to choose **metric** (km, m, km/h) or
**imperial** (mi, ft, mph). The choice flows through every page that
displays distances, elevations, or wind speeds.

Build a route
-------------

#. Open the route list (``/routes/``) and click **New route**.
#. Click on the map to place waypoints. Each click extends the route via the
   OSRM bike profile, snapping to cycling-friendly roads.
#. Drag a marker to move it. The route re-snaps automatically.
#. Use the toolbar to undo the last point or clear the route entirely.
#. Give the route a name and description, then save. The app fetches an
   elevation profile from Open-Meteo in the background and computes total
   distance and elevation gain.

Import a route
--------------

From the route list click **Import**. Supported formats are GPX, TCX, FIT,
KML, and KMZ. The file extension determines the parser; if a file fails to
parse you'll see an error message and the upload form again.

Export a route
--------------

On the route detail page, the **Export** menu offers GPX, TCX, FIT, KML,
and KMZ downloads. The FIT export is a Garmin Course file, suitable for
loading onto a head unit as a route to follow.

Schedule a ride
---------------

#. Open the calendar at ``/planning/``.
#. Click **Add ride** on a day.
#. Pick a route, set the date and time, and add notes.
#. Save. The ride appears in the calendar grid and on its own detail page.

View wind for a scheduled ride
------------------------------

The ride detail page shows the route polyline plus arrow markers along the
route showing wind direction (where the wind is *going*) and speed at the
ride's scheduled hour. Wind data is fetched live from Open-Meteo and
sampled at twelve evenly-spaced points along the route.

Rides scheduled more than ~16 days in the future may return no wind data
because they exceed the forecast horizon.
