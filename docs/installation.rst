Installation
============

Requirements
------------

* Python 3.11 or newer
* A virtual environment (the docs assume one at ``.venv/django_env``)
* Internet access at runtime — OSRM and Open-Meteo are called from the server

The third-party Python dependencies are pinned loosely in
``requirements.txt``: Django, ``gpxpy``, ``fitparse``, ``lxml``, and
``requests``.

Setup
-----

On Windows (bash):

.. code-block:: bash

   VENV="./.venv/django_env/Scripts"
   $VENV/pip.exe install -r requirements.txt
   $VENV/python.exe manage.py migrate
   $VENV/python.exe manage.py createsuperuser
   $VENV/python.exe manage.py runserver

Then open http://127.0.0.1:8000.

External services
-----------------

Both default to free, keyless public endpoints:

* **OSRM** — ``routing.openstreetmap.de/routed-bike``. Used to snap
  click-points to cycling-friendly roads. The public instance is
  rate-limited; for heavy use, run a local OSRM container and set
  ``OSRM_BASE_URL`` in :mod:`planner_project.settings`.
* **Open-Meteo** — ``api.open-meteo.com``. Used for hourly wind data on
  scheduled rides and for elevation lookups on saved routes. Forecast horizon
  is roughly 16 days, so rides scheduled further out will return null wind
  values.

Running the test suite
----------------------

.. code-block:: bash

   $VENV/python.exe manage.py test

Building the docs
-----------------

.. code-block:: bash

   $VENV/pip.exe install sphinx sphinx-rtd-theme
   cd docs
   ../$VENV/sphinx-build.exe -b html . _build/html

Open ``docs/_build/html/index.html`` to view the result.
