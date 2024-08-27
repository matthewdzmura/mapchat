from mapchat.backends.location_history_backend import LocationHistoryBackend
from tests.backends.helpers import set_up_location_history_backend_table, tear_down_location_history_backend_table

import googlemaps
import json
import responses
import sqlite3
import unittest


class LocationHistoryBackendTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        set_up_location_history_backend_table(self.conn)
        self.gmaps = googlemaps.Client("AIzaasdf")

    def tearDown(self):
        tear_down_location_history_backend_table(self.conn)
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
                    "name": "Restaurant"
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
                    "name": "Laundromat"
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
                    "name": "Grocery Store"
                }
            },
            status=200,
            content_type="application/json",
        )

        # Populate!
        backend.populate_location_history(lh)

        # Check contents of tables.
        # First check all the visits are populated.
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

        # Now check the raw place infos are there.
        rows = cursor.execute(
            "SELECT * from raw_place ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], 'place_id1')
        self.assertEqual(
            json.loads(rows[0][1]),
            json.loads('{"place_id": "place_id1", "name": "Restaurant"}'))
        self.assertEqual(rows[1][0], 'place_id2')
        self.assertEqual(
            json.loads(rows[1][1]),
            json.loads('{"place_id": "place_id2", "name": "Laundromat"}'))
        self.assertEqual(rows[2][0], 'place_id3')
        self.assertEqual(
            json.loads(rows[2][1]),
            json.loads('{"place_id": "place_id3", "name": "Grocery Store"}'))

        # Finally check to see if the structured places are there.
        rows = cursor.execute(
            "SELECT * from places ORDER BY place_id").fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], 'place_id1')
        self.assertEqual(rows[0][1], 'Restaurant')
        self.assertEqual(rows[1][0], 'place_id2')
        self.assertEqual(rows[1][1], 'Laundromat')
        self.assertEqual(rows[2][0], 'place_id3')
        self.assertEqual(rows[2][1], 'Grocery Store')

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
                    "name": "Grocery Store"
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
            json.loads('{"place_id": "place_id3", "name": "Grocery Store"}'))

    def test_insert_place_info(self):
        # Sample place dictionary
        place = {
            'place_id':
            'test_place_id',
            'name':
            'Test Place',
            'formatted_address':
            '123 Test St',
            'geometry': {
                'location': {
                    'lat': 12.34,
                    'lng': 56.78
                },
                'viewport': {
                    'northeast': {
                        'lat': 12.35,
                        'lng': 56.79
                    },
                    'southwest': {
                        'lat': 12.33,
                        'lng': 56.77
                    }
                }
            },
            'types': ['restaurant', 'bar'],
            'address_components': [{
                'long_name': 'Test City',
                'short_name': 'TC',
                'types': ['locality']
            }],
            'opening_hours': {
                'open_now':
                True,
                'periods': [{
                    'open': {
                        'day': 1,
                        'time': '0800'
                    },
                    'close': {
                        'day': 1,
                        'time': '2200'
                    }
                }]
            },
            'photos': [{
                'height': 800,
                'width': 600,
                'photo_reference': 'photo_ref',
                'html_attributions': ['<a href="test">Test</a>']
            }],
            'reviews': [{
                'author_name': 'John Doe',
                'author_url': 'http://example.com',
                'language': 'en',
                'profile_photo_url': 'http://example.com/photo.jpg',
                'rating': 4.5,
                'relative_time_description': '2 days ago',
                'text': 'Great place!',
                'time': 1616161616
            }]
        }

        # Call the function
        backend = LocationHistoryBackend(self.conn, self.gmaps)
        backend._insert_place_info(place)

        # Verify the data was inserted correctly
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM places WHERE place_id = ?',
                       ('test_place_id', ))
        place_row = cursor.fetchone()
        self.assertIsNotNone(place_row)
        self.assertEqual(place_row[0], 'test_place_id')
        self.assertEqual(place_row[1], 'Test Place')
        self.assertEqual(place_row[2], '123 Test St')
        self.assertEqual(place_row[30], 12.34)
        self.assertEqual(place_row[31], 56.78)
        self.assertEqual(place_row[32], 12.35)
        self.assertEqual(place_row[33], 56.79)
        self.assertEqual(place_row[34], 12.33)
        self.assertEqual(place_row[35], 56.77)
        self.assertEqual(json.loads(place_row[36]), ['restaurant', 'bar'])

        cursor.execute('SELECT * FROM address_components WHERE place_id = ?',
                       ('test_place_id', ))
        address_component_row = cursor.fetchone()
        self.assertIsNotNone(address_component_row)
        self.assertEqual(address_component_row[2], 'Test City')
        self.assertEqual(address_component_row[3], 'TC')
        self.assertEqual(json.loads(address_component_row[4]), ['locality'])

        cursor.execute('SELECT * FROM opening_hours WHERE place_id = ?',
                       ('test_place_id', ))
        opening_hours_row = cursor.fetchone()
        self.assertIsNotNone(opening_hours_row)
        self.assertTrue(opening_hours_row[1])

        cursor.execute(
            'SELECT * FROM opening_periods WHERE opening_hours_id = ?',
            (opening_hours_row[0], ))
        opening_period_row = cursor.fetchone()
        self.assertIsNotNone(opening_period_row)
        self.assertEqual(opening_period_row[2], 1)
        self.assertEqual(opening_period_row[3], '0800')
        self.assertEqual(opening_period_row[4], 1)
        self.assertEqual(opening_period_row[5], '2200')

        cursor.execute('SELECT * FROM photos WHERE place_id = ?',
                       ('test_place_id', ))
        photo_row = cursor.fetchone()
        self.assertIsNotNone(photo_row)
        self.assertEqual(photo_row[2], 800)
        self.assertEqual(photo_row[3], 600)
        self.assertEqual(photo_row[4], 'photo_ref')
        self.assertEqual(json.loads(photo_row[5]), ['<a href="test">Test</a>'])

        cursor.execute('SELECT * FROM reviews WHERE place_id = ?',
                       ('test_place_id', ))
        review_row = cursor.fetchone()
        self.assertIsNotNone(review_row)
        self.assertEqual(review_row[2], 'John Doe')
        self.assertEqual(review_row[3], 'http://example.com')
        self.assertEqual(review_row[4], 'en')
        self.assertEqual(review_row[6], 'http://example.com/photo.jpg')
        self.assertEqual(review_row[7], 4.5)
        self.assertEqual(review_row[8], '2 days ago')
        self.assertEqual(review_row[9], 'Great place!')
        self.assertEqual(review_row[10], 1616161616)


if __name__ == '__main__':
    unittest.main()
