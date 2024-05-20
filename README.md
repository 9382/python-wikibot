# Python-WikiBot

A tool used for running wikipedia bots, developed for and used by [Aidan9382-Bot](https://en.wikipedia.org/wiki/User:Aidan9382-Bot)

## Requirements

Python (Tested on v3.8, but it should work on most future versions) with the following modules:
* requests
* python-dotenv
* colorama

You must provide the Username and Password (or [BotPassword](https://en.wikipedia.org/wiki/Special:BotPasswords)) of the bot, along with some other settings, in a `.env` file. See `.env-example` for a reference

## Usage

To run the bot and its tasks, run `main.py`. All options required for the bot are handled from the `.env` file. To test the primary wikitools module standalone, run `wikitools.py` for a live test environment

## Notes and Warnings

If you plan to use the base script to run your own bot, please do not use the tasks provided in /Tasks/. These are simply there to show the code behind the tasks I use for my own bot. Due to [WP:BRFA](https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval), you will not be allowed to run them on your own bot without prior approval.

While this tool works and is in active use, it could potentially be buggy in more extreme and untested cases. It is also not designed with execution speed as its primary goal, and therefore may be slow for certain tasks.
