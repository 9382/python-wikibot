# Python-WikiBot

Python-WikiBot is a tool used for running wikipedia bots and their tasks.

## Requirements

Python (Only tested on v3.8, but it should work on most future and some previous versions).

The requests and dotenv modules. All other modules should come with Python

You must provide the Username and Password of the bot, along with some other stuff, in a `.env` file (See `.env-example`)

## Notes and Warnings

If you plan to use the base script to run your own bot, please do not use the tasks provided in /Tasks/. These are simply there to show the code behind the tasks I use for my own bot. Due to [WP:BRFA](https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval), you will not be allowed to run them on your own bot without prior approval.

While this tool works, it doesn't have major testing, and could potentially be buggy or even broken in more extreme cases.
It is also not designed with ease of use or execution speed as its primary goal, and therefore may be unintuitive or slow.
If you intend to use this yourself, ensure that you have done proper testing to make sure it will do as you intend by trying it on your sandbox or similar places.
