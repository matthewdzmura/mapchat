from dateutil import parser

import googlemaps
import logging
import json
import os
import sqlite3
from typing import Any, Dict, List, Set, Tuple


class LocationHistoryBackend:
    """
    Provides a simple backend for reading Location History from a provided JSON
    string, fetching supporting place information from the Google Maps API, and
    storing the result in a sqlite3 database for further querying.

    A visit will be stored as a Tuple[int, int, str, str] where the fields are
        visit[0](int): Start timestamp of the visit (seconds since unix epoch)
        visit[1](int): End timestamp of the visit (seconds since unix epoch)
        visit[2](str): Place ID of the visit, a unique identifier that can be
            used to fetch supporting place details from the raw_place table or
            the GoogleMaps Places API.
        visit[3](str): Semantic type. Uses the following values:
            'HOME': A user's confirmed home
            'WORK': A user's confirmed work
            'INFERRED_HOME': A user's inferred home
            'INFERRED_WORK': A user's inferred work
            'SEARCHED_ADDRESS': An address in the user's search history.
            'UNKNOWN': Any other type of place visited inferred by Google's
                place inference system.

    Args:
            db (sqlite3.Connection): Connections to an existing sqlite3
                database initialized with the appropriate schema found
                in location_history_schema.sql.
            gmaps_client (googlemaps.Client, optional): A client for the Google
                Maps API that will be used to fetch supporting place details.
                If not provided, one will be initialized using the key found in
                the GOOGLEMAPS_KEY environment variable. Defaults to None.

        Raises:
            RuntimeError: Raised when a valid Google Maps client cannot be
                created because the GOOGLEMAPS_KEY env variable isn't found.
    """

    def __init__(self,
                 db: sqlite3.Connection,
                 gmaps_client: googlemaps.Client = None) -> None:
        self.db = db
        if gmaps_client is None:
            gmaps_key = os.getenv("GOOGLEMAPS_KEY", None)
            if gmaps_key is None:
                raise RuntimeError(
                    "Could not get environment variable GOOGLEMAPS_KEY."
                    "Google Maps API key is required to fetch information about places."
                )
            self.gmaps = googlemaps.Client(key=gmaps_key)
        else:
            self.gmaps = gmaps_client

    def _deduplicate_place_visits(
        self, new_visits: List[Tuple[int, int, str, str]]
    ) -> List[Tuple[int, int, str, str]]:
        """
        Given a list of visits, will remove any visits (based on start time)
        that are already in the database.

        Args:
            new_visits (List[Tuple[int, int, str, str]]): List of new visits.
                The fields are start time, end time, place id, and semantic
                type.

        Returns:
            List[Tuple[int, int, str, str]]: The list of filtered visits.
        """
        cur = self.db.cursor()
        rows = cur.execute("SELECT start_time FROM visit").fetchall()
        old_start_times = {row[0] for row in rows}
        return [
            visit for visit in new_visits if visit[0] not in old_start_times
        ]

    def populate_location_history(self, lh: dict) -> None:
        """
        Populates the database with all the visits provided by lh. Will
        addtionally fetch place details from the Google Maps API for any places
        that have not appeared as inputs in previous calls to
        populate_location_history.

        Args:
            lh (dict): JSON dictionary of the user's location history. This
            data can be downloaded from Google if the user has Location
            History enabled.
        """
        cur = self.db.cursor()
        visits = [(int(parser.isoparse(segment['startTime']).timestamp()),
                   int(parser.isoparse(segment['endTime']).timestamp()),
                   segment['visit']['topCandidate']['placeId'],
                   segment['visit']['topCandidate']['semanticType'])
                  for segment in lh['semanticSegments'] if 'visit' in segment]
        visits = self._deduplicate_place_visits(visits)

        cur.executemany(
            """
                        INSERT INTO visit
                        (start_time, end_time, place_id, semantic_type)
                        VALUES(?, ?, ?, ?)
                        """, visits)
        self.db.commit()
        self._populate_place_info(visits)

    def _deduplicate_place_ids(self, new_place_ids: Set[str]) -> Set[str]:
        """
        Deduplicates place ids against ones that are already in the raw_place
        table.

        Args:
            new_place_ids (Set[str]): Set of new place ids to be deduplicated.

        Returns:
            Set[str]: All place ids from new_place_ids that are not already in
                the raw_place table.
        """
        cur = self.db.cursor()
        rows = cur.execute("SELECT place_id FROM raw_place").fetchall()
        old_place_ids = {row[0] for row in rows}
        return new_place_ids - old_place_ids

    def _populate_place_info(self, visits: List[Tuple[int, int, str,
                                                      str]]) -> None:
        """
        Fetches place details for a list of visits and populate them in the
        raw_place table. If a place already has an entry, its data will not be
        refetched. Data will be fetched from the Google Maps Places API 
        (https://developers.google.com/maps/documentation/places/web-service/overview).

        Args:
            visits (List[Tuple[int, int, str, str]]): List of visits to fetch
                place details for. The third field for each visit is the place
                id which is used for the lookup.
        """
        new_place_ids = {visit[2] for visit in visits}
        place_ids = self._deduplicate_place_ids(new_place_ids)
        place_infos = []
        for place_id in place_ids:
            try:
                response = self.gmaps.place(place_id)
            except googlemaps.exceptions.ApiError as error:
                logging.error(error)
                logging.error("Failed to fetch place info for place id: " +
                              place_id)
            except googlemaps.exceptions.Timeout:
                logging.error("Timeout failure for place lookup")
            except:
                logging.error("Failed to fetch place info for place id: " +
                              place_id)
            else:
                if response['status'] != 'OK':
                    # TODO: Add error handling
                    continue
                place_info = response['result']
                # Populate the structured data.
                self._insert_place_info(place_info)
                place_info_json = json.dumps(place_info, indent=2)
                place_infos += [(place_id, place_info_json)]
        cur = self.db.cursor()
        cur.executemany(
            """INSERT INTO raw_place (place_id, place_info) VALUES(?, ?)""",
            place_infos)
        for place_info in place_infos:
            self._insert_place_info(json.loads(place_info[1]))
        self.db.commit()

    def _populate_structured_places_from_raw(self) -> None:
        """
        Reads all place info data from the raw_place table and inserts it into
        the structured place info tables.
        """
        cur = self.db.cursor()
        rows = cur.execute("SELECT * FROM raw_place").fetchall()
        for row in rows:
            place_info = json.loads(row[1])
            self._insert_place_info(place_info)

        # Function to insert data into the database
    def _insert_place_info(self, place: Dict) -> None:
        """
        Inserts place information into the database.

        Args:
            place (dict): A dictionary containing the place information.

        Returns:
            None
        """
        # Insert into places table
        cursor = self.db.cursor()
        lat = None
        lng = None
        ne_lat = None
        ne_lng = None
        sw_lat = None
        sw_lng = None
        if 'geometry' in place:
            if 'location' in place['geometry']:
                lat = place['geometry']['location'].get('lat')
                lng = place['geometry']['location'].get('lng')
            if 'viewport' in place['geometry']:
                ne_lat = place['geometry']['viewport']['northeast'].get('lat')
                ne_lng = place['geometry']['viewport']['northeast'].get('lng')
                sw_lat = place['geometry']['viewport']['southwest'].get('lat')
                sw_lng = place['geometry']['viewport']['southwest'].get('lng')
        cursor.execute(
            '''
            INSERT OR IGNORE INTO places (
                place_id, name, formatted_address, formatted_phone_number, international_phone_number, business_status,
                curbside_pickup, delivery, dine_in, reservable, serves_beer, serves_brunch, serves_dinner, serves_lunch,
                serves_vegetarian_food, serves_wine, takeout, price_level, rating, user_ratings_total, url, website,
                wheelchair_accessible_entrance, utc_offset, vicinity, icon, icon_background_color, icon_mask_base_uri,
                editorial_summary_language, editorial_summary_overview, geometry_location_lat, geometry_location_lng,
                geometry_viewport_northeast_lat, geometry_viewport_northeast_lng, geometry_viewport_southwest_lat,
                geometry_viewport_southwest_lng, categories
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (place['place_id'], place.get('name'),
             place.get('formatted_address'),
             place.get('formatted_phone_number'),
             place.get('international_phone_number'),
             place.get('business_status'), place.get('curbside_pickup'),
             place.get('delivery'), place.get('dine_in'),
             place.get('reservable'), place.get('serves_beer'),
             place.get('serves_brunch'), place.get('serves_dinner'),
             place.get('serves_lunch'), place.get('serves_vegetarian_food'),
             place.get('serves_wine'), place.get('takeout'),
             place.get('price_level'), place.get('rating'),
             place.get('user_ratings_total'), place.get('url'),
             place.get('website'), place.get('wheelchair_accessible_entrance'),
             place.get('utc_offset'), place.get('vicinity'), place.get('icon'),
             place.get('icon_background_color'),
             place.get('icon_mask_base_uri'), place.get(
                 'editorial_summary', {}).get('language'),
             place.get('editorial_summary', {}).get('overview'), lat, lng,
             ne_lat, ne_lng, sw_lat, sw_lng, json.dumps(place.get('types',
                                                                  []))))

        place_id = place['place_id']

        # Insert into address_components table
        for component in place.get('address_components', []):
            cursor.execute(
                '''
                INSERT INTO address_components (place_id, long_name, short_name, types)
                VALUES (?, ?, ?, ?)
                ''', (place_id, component.get('long_name'),
                      component.get('short_name'),
                      json.dumps(component.get('types', []))))

        # Insert into opening_hours and opening_periods tables
        if 'opening_hours' in place:
            cursor.execute(
                '''
                INSERT INTO opening_hours (place_id, open_now)
                VALUES (?, ?)
                ''', (place_id, place['opening_hours'].get('open_now')))
            opening_hours_id = cursor.lastrowid

            for period in place['opening_hours'].get('periods', []):
                open_day = period.get('open', {}).get('day')
                open_time = period.get('open', {}).get('time')
                close_day = period.get('close', {}).get('day')
                close_time = period.get('close', {}).get('time')
                cursor.execute(
                    '''
                    INSERT INTO opening_periods (opening_hours_id, open_day, open_time, close_day, close_time)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (opening_hours_id, open_day, open_time, close_day,
                          close_time))

        # Insert into special_days table
        if 'current_opening_hours' in place and 'special_days' in place[
                'current_opening_hours']:
            for special_day in place['current_opening_hours']['special_days']:
                cursor.execute(
                    '''
                    INSERT INTO special_days (opening_hours_id, date, exceptional_hours)
                    VALUES (?, ?, ?)
                    ''', (opening_hours_id, special_day.get('date'),
                          special_day.get('exceptional_hours')))

        # Insert into secondary_opening_hours and secondary_opening_periods tables
        for secondary_hours in place.get('secondary_opening_hours', []):
            cursor.execute(
                '''
                INSERT INTO secondary_opening_hours (place_id, type, open_now)
                VALUES (?, ?, ?)
                ''', (place_id, secondary_hours.get('type'),
                      secondary_hours.get('open_now')))
            secondary_opening_hours_id = cursor.lastrowid

            for period in secondary_hours.get('periods', []):
                cursor.execute(
                    '''
                    INSERT INTO secondary_opening_periods (secondary_opening_hours_id, open_day, open_time, close_day, close_time, open_date, close_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (secondary_opening_hours_id, period.get(
                        'open', {}).get('day'), period.get(
                            'open', {}).get('time'), period.get(
                                'close', {}).get('day'), period.get(
                                    'close', {}).get('time'),
                     period.get('open', {}).get('date'), period.get(
                         'close', {}).get('date')))

        # Insert into photos table
        for photo in place.get('photos', []):
            cursor.execute(
                '''
                INSERT INTO photos (place_id, height, width, photo_reference, html_attributions)
                VALUES (?, ?, ?, ?, ?)
                ''', (place_id, photo.get('height'), photo.get('width'),
                      photo.get('photo_reference'),
                      json.dumps(photo.get('html_attributions', []))))

        # Insert into reviews table
        for review in place.get('reviews', []):
            cursor.execute(
                '''
                INSERT INTO reviews (place_id, author_name, author_url, language, original_language, profile_photo_url, rating, relative_time_description, text, time, translated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (place_id, review.get('author_name'), review.get('author_url'),
                 review.get('language'), review.get('original_language'),
                 review.get('profile_photo_url'), review.get('rating'),
                 review.get('relative_time_description'), review.get('text'),
                 review.get('time'), review.get('translated')))

        # Commit the changes
        self.db.commit()

    def query_visits(self) -> List[Tuple[int, int, str, str]]:
        """
        Fetches all visits from the table.

        Returns:
            List[Tuple[int, int, str, str]]: Visits that were fetched.
        """
        cur = self.db.cursor()
        return cur.execute("SELECT * FROM visit").fetchall()

    def execute_query(self, query: str) -> List[Tuple[Any]]:
        """
        Executes a SQL query on a sqlite3 database and returns the results.

        Args:
            query (str): SQL query to be executed.

        Returns:
            List[Tuple[Any]]: Results of the query.
        """
        # Connect to the database
        cursor = self.db.cursor()

        # Execute the query
        cursor.execute(query)

        # Fetch all results
        return cursor.fetchall()
