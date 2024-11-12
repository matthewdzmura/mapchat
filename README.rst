MapChat
======

A basic RAG application for chatting with an LLM about places you've been.

Overview
------
MapChat allows you to have natural language conversations about your location history data. Upload your Google Location History and ask questions like "Where did I go last summer?" or "How many times have I been to New York?" MapChat uses Google's Gemini LLM to understand your questions and translate them into SQL queries against your location data.

Features
------
* Upload and store Google Location History data
* Natural language interface powered by Gemini
* Persistent chat history
* Web-based interface built with Flask

Installation
------
* Clone the repository
* Install dependencies::

    $ pip install .

Set up your environment variables::

    $ export GEMINI_API_KEY="your_api_key_here"
    $ export GOOGLE_MAPS_API_KEY="your_api_key_here"

Usage
------
Start the Flask server::

    $ flask --app mapchat run

Navigate to http://localhost:5000 in your browser

Click "Upload Location History" and follow the instructions to upload your Google Location History JSON file

Return to the chat interface and start asking questions about your location history

Testing
------
    $ python -m unittest

Requirements
------
* Python 3.11+
* Flask
* Google Maps API
* Google Generative AI (Gemini)
* SQLite3

Project Structure
------
* agent - Core chat functionality and Gemini integration
* backends - Database interaction for chat and location history
* templates - Flask HTML templates
* tests - Unit tests

License
------
BSD 3-Clause License

Maintainers
------
Matt D'Zmura