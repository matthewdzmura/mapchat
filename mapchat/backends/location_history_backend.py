from dateutil import parser

import googlemaps
import logging
import json
import os
import sqlite3
from typing import List, Set, Tuple


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
        self._populate_raw_place_info(visits)

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

    def _populate_raw_place_info(
            self, visits: List[Tuple[int, int, str, str]]) -> None:
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
                place_info_json = json.dumps(place_info, indent=2)
                place_infos += [(place_id, place_info_json)]
        cur = self.db.cursor()
        cur.executemany(
            """INSERT INTO raw_place (place_id, place_info) VALUES(?, ?)""",
            place_infos)
        self.db.commit()

    def query_visits(self) -> List[Tuple[int, int, str, str]]:
        """
        Fetches all visits from the table.

        Returns:
            List[Tuple[int, int, str, str]]: Visits that were fetched.
        """
        cur = self.db.cursor()
        return cur.execute("SELECT * FROM visit").fetchall()
