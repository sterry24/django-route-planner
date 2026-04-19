django-route-planner
====================

A Django web app for planning cycling routes and scheduling rides, with a
wind-forecast overlay on the route for the scheduled time.

The app models the core RideWithGPS flow — draw a route on a map, snap it to
cycling-friendly roads via OSRM, save it to a per-user library, and import or
export GPX / TCX / FIT / KML / KMZ files. Scheduled rides on a calendar pick
up an hourly wind forecast from Open-Meteo and overlay it on the map at the
ride's time.

.. toctree::
   :maxdepth: 2
   :caption: User guide

   installation
   usage

.. toctree::
   :maxdepth: 2
   :caption: Developer guide

   architecture
   api/routes
   api/planning
   api/accounts


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
