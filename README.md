# Python-WikiBot

Python-WikiBot is a tool used for running wikipedia bots and their tasks.

## Notes and Warnings

If you plan to use the base script to run your own bot, please do not use the tasks provided in /Tasks/. These are simply there to show examples of tasks i have used personally, or to show others how im doing something. Due to BRFA and other similar processes, you will probably not be allowed to run them on your own bot without prior approval.

While this tool is confirmed to work, it has minimal testing, and could potentially be buggy in untested cases.
It is also not designed with ease of use or execution speed as its primary goal, and therefore may be unintuitive or slow.
If you intend to use this yourself, ensure that you have done proper testing to make sure it will do as you intend by trying it on your sandbox.

## Requirements

Python (Only tested on v3.8, but it should work on most future and some previous versions).

The requests and dotenv modules. All other modules should come with Python

You must provide the Username and Password of the bot in a .env file (See .env-example)
