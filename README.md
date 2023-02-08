# Python-WikiBot

Python-WikiBot is a tool used for running wikipedia bots and their tasks.

## Requirements

Python (Only tested on v3.8, but it should work on most future versions).

Some modules (Couldn't tell you which ones, just run it and pip install anything you don't have)

You must provide the Username and Password of the bot, along with some other stuff, in a `.env` file (See `.env-example`). [BotPasswords](https://en.wikipedia.org/wiki/Special:BotPasswords) are *not* currently supported, and attempting to use one will lead to a failed attempt to login.

## Usage

To run the bot, run `main.py`. All options required for the bot are handled from the `.env` file. <!-- Could use more detail, but dunno what to say -->

## Notes and Warnings

If you plan to use the base script to run your own bot, please do not use the tasks provided in /Tasks/. These are simply there to show the code behind the tasks I use for my own bot. Due to [WP:BRFA](https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval), you will not be allowed to run them on your own bot without prior approval.

While this tool works and is in active use, it could potentially be buggy in more extreme and untested cases.
It is also not designed with ease of use or execution speed as its primary goal, and therefore may be unintuitive or slow.
