from mapchat.backends.location_history_backend import LocationHistoryBackend

import googlemaps
import json
import responses
import sqlite3
import unittest


class LocationHistoryBackendTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        cursor = self.conn.cursor()
        cursor.executescript("""
            DROP TABLE IF EXISTS visit;
            DROP TABLE IF EXISTS raw_place;

            CREATE TABLE visit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                place_id TEXT NOT NULL,
                semantic_type TEXT
                    CHECK( semantic_type IN
                    ('UNKNOWN', 'HOME', 'WORK', 'INFERRED_HOME', 'INFERRED_WORK', 'SEARCHED_ADDRESS'))
                    NOT NULL DEFAULT 'UNKNOWN'
            );

            CREATE TABLE raw_place (
                place_id TEXT PRIMARY KEY,
                place_info TEXT NOT NULL
            );
        """)
        self.conn.commit()
        self.gmaps = googlemaps.Client("AIzaasdf")

    def tearDown(self):
        self.conn.close()

    @responses.activate
    def test_populate_location_history(self):
        # Create the backend.
        with open("tests/backends/assets/test_lh.txt", "r") as f:
            lh = json.loads(f.read())
        backend = LocationHistoryBackend(self.conn, self.gmaps)

        # Mock the requests to the Google Maps API.
        url1 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id1&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url1,
            json={
                "status": "OK",
                "html_attributions": [],
                "result": {
                    "place_id": "place_id1",
                    "place_name": "Restaurant"
                }
            },
            status=200,
            content_type="application/json",
        )
        url2 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id2&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url2,
            json={
                "status": "OK",
                "html_attributions": [],
                "result": {
                    "place_id": "place_id2",
                    "place_name": "Laundromat"
                }
            },
            status=200,
            content_type="application/json",
        )
        url3 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id3&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url3,
            json={
                "status": "OK",
                "html_attributions": [],
                "result": {
                    "place_id": "place_id3",
                    "place_name": "Grocery Store"
                }
            },
            status=200,
            content_type="application/json",
        )

        # Populate!
        backend.populate_location_history(lh)

        # Check contents of tables.
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM visit").fetchall()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0],
                         (1, 1331658957, 1331664540, 'place_id1', 'UNKNOWN'))
        self.assertEqual(rows[1],
                         (2, 1331681205, 1331684849, 'place_id2', 'UNKNOWN'))
        self.assertEqual(rows[2],
                         (3, 1331684849, 1331688449, 'place_id1', 'UNKNOWN'))
        self.assertEqual(rows[3],
                         (4, 1331692049, 1331695649, 'place_id3', 'UNKNOWN'))

        rows = cursor.execute(
            "SELECT * from raw_place ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], 'place_id1')
        self.assertEqual(
            json.loads(rows[0][1]),
            json.loads(
                '{"place_id": "place_id1", "place_name": "Restaurant"}'))
        self.assertEqual(rows[1][0], 'place_id2')
        self.assertEqual(
            json.loads(rows[1][1]),
            json.loads(
                '{"place_id": "place_id2", "place_name": "Laundromat"}'))
        self.assertEqual(rows[2][0], 'place_id3')
        self.assertEqual(
            json.loads(rows[2][1]),
            json.loads(
                '{"place_id": "place_id3", "place_name": "Grocery Store"}'))

        # Let's try populating again with more history.
        # Make sure we're not making duplicate calls for place infos.
        with open("tests/backends/assets/test_lh2.txt", "r") as f2:
            lh2 = json.loads(f2.read())

        # Populate!
        backend.populate_location_history(lh2)

        # Check contents of tables.
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM visit").fetchall()
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[4],
                         (5, 1334337357, 1334342940, 'place_id1', 'UNKNOWN'))
        self.assertEqual(rows[5],
                         (6, 1334359605, 1334363249, 'place_id2', 'UNKNOWN'))

        rows = cursor.execute(
            "SELECT * from raw_place ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 3)

        # Try adding the same location history data in again. This should be a no op.
        backend.populate_location_history(lh)

        # Check contents of tables.
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM visit").fetchall()
        self.assertEqual(len(rows), 6)
        rows = cursor.execute(
            "SELECT * from raw_place ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 3)

    @responses.activate
    def test_place_info_api_error(self):
        # Create the backend.
        with open("tests/backends/assets/test_lh.txt", "r") as f:
            lh = json.loads(f.read())
        backend = LocationHistoryBackend(self.conn, self.gmaps)

        # Mock the requests to the Google Maps API.
        url1 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id1&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url1,
            json={"status": "MISSING"},
            status=200,
            content_type="application/json",
        )
        url2 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id2&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url2,
            json={},
            status=404,
            content_type="application/json",
        )
        url3 = "https://maps.googleapis.com/maps/api/place/details/json?placeid=place_id3&reviews_sort=most_relevant&key=AIzaasdf"
        responses.add(
            responses.GET,
            url3,
            json={
                "status": "OK",
                "html_attributions": [],
                "result": {
                    "place_id": "place_id3",
                    "place_name": "Grocery Store"
                }
            },
            status=200,
            content_type="application/json",
        )

        # Populate!
        backend.populate_location_history(lh)

        # Make sure only place 3 is populated.
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT * from raw_place ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "place_id3")
        self.assertEqual(
            json.loads(rows[0][1]),
            json.loads(
                '{"place_id": "place_id3", "place_name": "Grocery Store"}'))


if __name__ == '__main__':
    unittest.main()
