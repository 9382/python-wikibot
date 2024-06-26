#coding: utf-8
# [!] If you need to change the basic settings of the bot, please see the .env-example, not here
# [?] This file only handles logging in and maintenance of tasks. For the backend of all the tools, see wikitools.py

from dotenv import dotenv_values
import traceback
import threading
import requests
import time
import os

if not os.path.exists("wikitools.py"):
    print("main.py appears to have been loaded from the wrong directory (no wikitools.py found). Closing in 5 seconds...")
    time.sleep(5)
    exit()

#See wikitools.py for all the classes and functions that form the primary tools
from wikitools import *

envvalues = dotenv_values()
EnabledTasks = envvalues["TASKS"].lower().replace(", ", ",").split(",")

DidLogin, username = AttemptLogin(envvalues["USER"], envvalues["PASS"])
if not DidLogin:
    print("Closing in 5 seconds...")
    time.sleep(5)
    exit()

#Task loader
WasForceExit = False
log("Attempting to load tasks...")
def BeginTaskCycle(func, funcName=None):
    global WasForceExit
    if not funcName:
        funcName = repr(func)
    while True:
        log(f"[Tasks] Beginning task cycle for {funcName}")
        try:
            func() #Begin task cycle
        except (requests.ConnectionError, requests.Timeout) as exc:
            #Revive threads that died due to connection errors
            lerror(f"[Tasks] Function {funcName} just threw a timeout error: {exc}\nThis thread will restart soon...")
            time.sleep(10)
            continue
        except KeyboardInterrupt:
            lalert("Force-exiting thread without restart due to a KeyboardInterrupt")
            WasForceExit = True
            break
        except BaseException as exc:
            lerror(f"[Tasks] Function {funcName} just threw a critical (not request based) error: {traceback.format_exc()}\nThis thread will restart in 5 minutes...")
            time.sleep(300)
            continue
        else:
            lwarn(f"[Tasks] Function {funcName} exited the loop without error, and so will not be restarterd")
            break
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
    filename = file[:-3] #Removes .py extension
    if not os.path.isfile("Tasks/"+file):
        if file != "__pycache__":
            verbose("Tasks", f"{file} is a subfolder and shouldn't be within the /Tasks")
        continue
    if not file.endswith(".py"):
        verbose("Tasks", f"{file} doesn't end with .py, it shouldn't be within the /Tasks")
        continue
    if filename.lower() in EnabledTasks:
        log(f"[Tasks] Running task {file}")
        try:
            ImportedTask = __import__(f"Tasks.{filename}", globals(), locals(), [], 0).__dict__[filename]
            #While this works, it feels somewhat stupid, but we go with it
        except Exception as exc:
            lerror(f"[Tasks] Task {file} import error -> {traceback.format_exc()}")
        else:
            taskThread = threading.Thread(target=BeginTaskCycle, args=(ImportedTask.__main__, filename), name=filename, daemon=True)
            taskThread.start()
    else:
        log(f"[Tasks] Skipping task {file} as it is not enabled")
lsucc("Finished loading tasks")

#Constant safety checks
def panicCheck():
    global username
    expectedTaskCount = threading.active_count()
    while True:
        time.sleep(20)
        tasks = threading.active_count()
        # log(f"Active task count: {tasks-1}")
        if tasks == 1:
            lalert("All tasks seem to have been terminated or finished")
            break
        elif tasks < expectedTaskCount:
            lwarn(f"We seem to have dropped from {expectedTaskCount}+1 tasks to {tasks}+1 - Could be a one-off task, but there may have also been an error")
        expectedTaskCount = tasks
        #Verify we're logged in and not stopped
        try:
            requestapi("get", "action=query&assert=user") #Force an assert=user test
            panic = Article(f"User:{username}/panic")
            if panic.Exists:
                if panic.GetContent().strip().lower() == "true":
                    SetStopped(True)
                else:
                    SetStopped(False)
            else:
                lalert(f"Panic page (User:{username}/panic) doesn't exist, stopping for safety")
                SetStopped(True)
        except Exception as exc:
            if type(exc) == APIException and exc.code == "assertuserfailed":
                lerror(f"assert=user has failed as we appear to be logged out. Re-requesting login...")
                SetStopped(True)
                DidLogin, username = AttemptLogin(envvalues["USER"], envvalues["PASS"])
                if not DidLogin:
                    lerror("Failed to log back in.")
                else:
                    lsucc("Managed to log back in. Resuming tasks...")
                    SetStopped(False)
            else:
                lerror(f"panic check had an error. Reason: {exc}")
                SetStopped(True)
BeginTaskCycle(panicCheck, "Main Loop")
if not WasForceExit:
    input("\nPress enter to exit...")
