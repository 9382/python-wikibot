#coding: utf-8
# [!] If you need to change the basic settings of the bot, please see the .env-example, not here
# [?] This file only handles logging in and maintenance of tasks. For the backend of the tools, see wikitools.py

from dotenv import dotenv_values
import traceback
import threading
import time
import os

#See wikitools.py for all the classes and functions that form the primary tools
from wikitools import *

envvalues = dotenv_values()
EnabledTasks = envvalues["TASKS"].lower().replace(", ", ",").split(",")
username, password = dotenv_values()["USER"], dotenv_values()["PASS"]

DidLogin = AttemptLogin(username, password)
if not DidLogin:
    print("Closing in 5 seconds...")
    time.sleep(5)
    exit()

#Task loader
log("Attempting to load tasks...")
def OnThreadError(args):
    out = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    thread = args.thread
    threadName = "<unknown>"
    if thread:
        threadName = thread.name
    lerror(f"[Task Manager] Exception on thread {threadName}:\n{out}")
threading.excepthook = OnThreadError
execList = {}
#Odd approach but it works
for file in os.listdir("Tasks"):
    if not os.path.isfile("Tasks/"+file):
        if file != "__pycache__":
            verbose("Tasks", f"{file} is a subfolder and shouldn't be within the /Tasks")
        continue
    if not file.endswith(".py"):
        verbose("Tasks", f"{file} doesn't end with .py, it shouldn't be within the /Tasks")
        continue
    if file[:-3].lower() in EnabledTasks: #Removes .py extension
        log(f"[Tasks] Running task {file}")
        try:
            exec(f"from Tasks import {file[:-3]} as ImportedTask")
            # If someone could please tell me how the hell to do this with importlib or __import__ that would be wonderful
            # Because I tried for like 20 minutes but it was being uncooperative
        except Exception as exc:
            lerror(f"[Tasks] Task {file} import error -> {traceback.format_exc()}")
        else:
            try:
                taskThread = threading.Thread(target=ImportedTask.__main__, name=file[:-3])
                taskThread.start()
            except Exception as exc:
                lerror(f"[Tasks] Task {file} execution error -> {traceback.format_exc()}")
    else:
        log(f"[Tasks] Skipping task {file} as it is not enabled")
lsucc("Finished loading tasks")

#Constant safety checks
while True:
    time.sleep(30)
    tasks = threading.active_count()
    # log(f"Active task count: {tasks-1}")
    if tasks == 1:
        lalert("All tasks seem to have been terminated or finished")
        break
    #Verify we're logged in and not stopped
    try:
        confirmStatus = requestapi("get", "action=query&assert=user")
    except Exception as exc:
        lerror(f"assert=user request had an error. Reason: {exc}")
        activelyStopped = True
    else:
        panic = Article(f"User:{username}/panic")
        if panic.exists:
            if panic.GetContent().strip().lower() == "true":
                activelyStopped = True
            else:
                activelyStopped = False
        else:
            lwarm(f"Panic page (User:{username}/panic) doesn't exist, stopping for safety")
            activelyStopped = True
input("Press enter to exit...")
