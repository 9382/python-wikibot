#coding: utf-8
# [!] Do NOT edit this file unless you know what you are doing, as these are core functions.

__all__ = [
        "verbose", "log", "lerror", "lalert", "lwarn", "lsucc",
        "Article", "Template", "Revision", "IterateCategory", "WikiConfig",
        "username", "userid", "AttemptLogin", "SetStopped",
        "requestapi", "CreateAPIFormRequest" #Avoid using these directly unless required
]

from dotenv import dotenv_values
import urllib.parse
import re as regex
import threading
import traceback
import colorama
import datetime
import requests
import random
import json
import time
import os
#For an explenation of the config options below, please see the .env-example file
envvalues = dotenv_values()
SUBMITEDITS = envvalues["SUBMITEDITS"].lower() == "true"
INDEV = envvalues["INDEV"].lower() == "true"
maxActionsPerMinute = int(envvalues["EDITSPERMIN"])
maxEdits = int(envvalues["MAXEDITS"])

isVerbose = envvalues["VERBOSE"].lower() == "true"
def verbose(origin, content):
    if isVerbose:
        print(f"[Verbose {origin}] {content}")

colorama.init()

def currentDate():
    #The current date in YYYY-MM-DD hh:mm:ss
    return str(datetime.datetime.fromtimestamp(time.time()//1))
def safeWriteToFile(filename, content, mode="w", encoding="UTF-8"):
    #Writes contents to a file, auto-creating the directory should it be missing
    if filename.find("\\") > -1:
        try:
            os.makedirs("/".join(filename.replace("\\", "/").split("/")[:-1]), exist_ok=True)
        except:
            return False, f"Couldnt make directory for {filename}"
    try:
        file = open(filename, mode, encoding=encoding, newline="")
    except:
        return False, f"Failed to open {filename}"
    try:
        file.write(content)
    except Exception as exc:
        file.close()
        return False, f"Failed to write content for {filename}"
    file.close()
    return True, f"Successfully wrote to {filename}"
def log(content, *, colour=""):
    #Manages the writing to a day-based log file for debugging
    prefixText = f"{currentDate()[11:]} - {threading.current_thread().name}"
    print(f"{colour}[Log {prefixText}] {content}\033[0m")
    success, result = safeWriteToFile(f"Logs/{currentDate()[:10]}.log", f"[{prefixText}] {content}\n", "a")
    if not success:
        print(f"\033[41m\033[30m[Log {prefixText}] Failed to write to log file: {result}\033[0m")
    return success
def lerror(content): #Black text, red background
    return log(content, colour="\033[41m\033[30m")
def lalert(content): #Red text
    return log(content, colour="\033[31m")
def lwarn(content): #Yellow text
    return log(content, colour="\033[33m")
def lsucc(content): #Green text
    return log(content, colour="\033[32m")

activelyStopped = False
APS = 60/maxActionsPerMinute
lastActionTime = 0
actionCount = 0

if SUBMITEDITS:
    log("SUBMITEDITS is set to True. Edits will actually be made")
else:
    log("SUBMITEDITS is set to False. Edits will not be requested, only simulated")
username, password = dotenv_values()["USER"], dotenv_values()["PASS"]
enwiki = "https://en.wikipedia.org/"
cookies = {}
def request(method, page, **kwargs):
    #Central request handler, used for automatically sorting cookies
    #Currently unused in favour of requestapi, but kept just in case
    global cookies
    startTime = time.perf_counter()
    request = getattr(requests, method)(enwiki+page, cookies=cookies, **kwargs)
    timeTaken = time.perf_counter() - startTime
    if timeTaken > 2.5:
        lwarn(f"[request] Just took {timeTaken}s to complete a single request - are we running alright?")
    if "set-cookie" in request.headers:
        verbose("request", "Attempting to note down some new cookies")
        setcookies = request.headers["set-cookie"].split(", ")
        for cookie in setcookies:
            actualCookie = cookie.split(";")[0]
            moreInfo = actualCookie.split("=")
            if moreInfo[0].find(" ") > -1:
                continue
            cookies[moreInfo[0]] = "=".join(moreInfo[1:])
            # print("Set cookie", moreInfo[0], "with value", "=".join(moreInfo[1:]))
    return request
def requestapi(method, apimethod, **kwargs):
    #Similar to request, but also runs some automatic checks on the return content
    apirequest = request(method, "w/api.php?"+apimethod+"&format=json", **kwargs)
    data = apirequest.json()
    if "error" in data: #Request failed
        code,info = data["error"]["code"], data["error"]["info"]
        errormessage = f"[requestapi] API Request failed to complete for query '{apimethod}' | {code} - {info}"
        lerror(errormessage)
        raise Exception(errormessage)
    if "warnings" in data: #Request worked, though theres some issues
        for warntype,text in data["warnings"].items():
            lwarn(f"[requestapi] API Request {warntype} warning for query '{apimethod}' - {text['*']}")
    # print("Haha look at me its raw data man for",method,apimethod,data)
    return data
def GetTokenForType(actiontype):
    return requestapi("get", "action=query&meta=tokens&type=*")["query"]["tokens"][f"{actiontype}token"]
boundary = "-----------PYB"+str(random.randint(1e9, 9e9)) #Any obscure string works
verbose("request", f"Using boundary {boundary}")
def CreateAPIFormRequest(location, data):
    #For post-based api requests. Helps avoid the possiblity of url encoding issues
    finaltext = ""
    for key, value in data.items():
        finaltext += f"""{boundary}\nContent-Disposition: form-data; name="{key}"\n\n{value}\n"""
    finaltext += f"{boundary}--"
    return requestapi("post", location, data=finaltext.encode("utf-8"), headers={"Content-Type":f"multipart/form-data; boundary={boundary[2:]}"})

def CheckIfStopped():
    if activelyStopped:
        lalert("The thread has been paused from continuing while panic mode is active. Pausing thread...")
        while activelyStopped:
            time.sleep(5)
        lsucc("Panic mode is no longer active. Exiting pause...")
        return True
    return False
def SetStopped(state):
    global activelyStopped
    if state != activelyStopped:
        log(f"Setting panic state to {state}")
    activelyStopped = state

namespaces = ["User", "Wikipedia", "WP", "File", "MediaWiki", "Template", "Help", "Category", "Portal", "Draft", "TimedText", "Module"] #Gadget( definition) is deprecated
pseudoNamespaces = {"CAT":"Category", "H":"Help", "MOS":"Wikipedia", "WP":"Wikipedia", "WT":"Wikipedia talk",
                    "Project":"Wikipedia", "Project talk":"Wikipedia talk", "Image":"File", "Image talk":"File talk",
                    "WikiProject":"Wikipedia", "T":"Template", "MP":"Article", "P":"Portal", "MoS":"Wikipedia"} #Special cases that dont match normal sets
namespaceIDs = {"Article":0, "Talk":1, "User":2, "User talk":3, "Wikipedia":4, "Wikipedia talk":5, "File":6, "File talk":7,
                "MediaWiki":8, "MediaWiki talk":9, "Template":10, "Template talk":11, "Help":12, "Help talk":13,
                "Category":14, "Category talk":15, "Portal":100, "Portal talk":101, "Draft":118, "Draft talk":119,
                "TimedText":710, "TimedText talk":711, "Module":828, "Module talk":829, "Special":-1, "Media":-2}
def GetNamespace(identifier):
    #Simply gets the namespace of an article from its name
    if type(identifier) == str:
        for namespace in namespaces:
            if identifier.startswith(namespace+":"):
                return namespace
            if identifier.startswith(namespace+" talk:"):
                return namespace+" talk"
        prefix = identifier.split(":")[0]
        if prefix in pseudoNamespaces:
            return pseudoNamespaces[prefix]
        if identifier.startswith("Talk:"):
            return "Talk"
        if identifier.startswith("Special:"):
            return "Special"
        return "Article"
    elif type(identifier) == int:
        for namespace, nsid in namespaceIDs.items():
            if nsid == identifier:
                return namespace
def GetNamespaceID(articlename):
    return namespaceIDs[GetNamespace(articlename)]
def StripNamespace(articlename):
    namespace = GetNamespace(articlename)
    if namespace == "Article":
        return articlename
    else:
        return articlename[len(namespace)+1:]

def SubstituteIntoString(wholestr, substitute, start, end):
    return wholestr[:start]+substitute+wholestr[end:]
class Template: #Parses a template and returns a class object representing it
    def __init__(self, templateText):
        if type(templateText) != str or templateText[:2] != "{{" or templateText[-2:] != "}}":
            raise Exception(f"The text '{templateText}' is not a valid template")
        self.Original = templateText
        self.Text = templateText
        templateArgs = templateText[2:-2].split("|")
        self.Template = templateArgs[0].strip()
        args = {}
        for arg in templateArgs:
            splitarg = arg.split("=")
            key, item = splitarg[0], "=".join(splitarg[1:])
            if not item: #No key
                lowestKeyPossible = 1
                while True:
                    if lowestKeyPossible in args:
                        lowestKeyPossible += 1
                    else:
                        args[lowestKeyPossible] = arg.strip()
                        break
            else: #Key specified
                args[key.strip()] = item.strip()
        self.Args = args
    #The functions below are designed to respect the original template's format (E.g. its spacing)
    #Simply use the below functions, and then ask for self.Text for the new representation to use
    #TODO: Re-code the below, because its bloody stupid and has problems (we use regex?? why not just store whitespace seperately???)
    def ChangeKey(self, key, newkey): #Replaces one key with another, retaining the original data
        #NOTE: THIS CURRENTLY ASSUMES YOU ARE NOT ATTEMPTING TO CHANGE AN UNKEY'D NUMERICAL INDEXs
        if type(key) == int or key.isnumeric():
            verbose("Template", f"CK was told to change {key} to {newkey} in {self.Template} despite it being a numerical index")
        if not key in self.Args:
            raise KeyError(f"{key} is not a key in the Template")
        self.Args[newkey] = self.Args[key]
        self.Args.pop(key)
        keylocation = regex.compile(f"\| *{key} *=").search(self.Text)
        keytext = keylocation.group()
        self.Text = SubstituteIntoString(self.Text, keytext.replace(key, newkey), *keylocation.span())
    def ChangeKeyData(self, key, newdata): #Changes the contents of the key
        #NOTE: THIS CURRENTLY ASSUMES YOU ARE NOT ATTEMPTING TO CHANGE AN UNKEY'D NUMERICAL INDEX
        if type(key) == int or key.isnumeric():
            verbose("Template", f"CKD was told to change {key} to {newkey} in {self.Template} despite it being a numerical index")
        if not key in self.Args:
            raise KeyError(f"{key} is not a key in the Template")
        olddata = self.Args[key]
        self.Args[key] = newdata
        keylocation = regex.compile(f"\| *{key} *=").search(self.Text)
        target = self.Text[keylocation.start()+1:].split("|")[0]
        self.Text = SubstituteIntoString(self.Text, target.replace(olddata, newdata), keylocation.start()+1, keylocation.start()+len(target)+1)

revisionMoveRegex = regex.compile('^(.+?) moved page \[\[([^\]]+)\]\] to \[\[([^\]]+)\]\]')
class Revision: #For getting the history of pages
    def __init__(self, data, diff=None):
        self.ID = data["revid"]
        self.ParentID = data["parentid"]
        self.User = ("userhidden" in data and "< User hidden >") or data["user"]
        self.Timestamp = data["timestamp"][:-1] #Strip the ending Z for datetime
        self.Date = datetime.datetime.fromisoformat(self.Timestamp)
        self.Age = (datetime.datetime.now() - self.Date).total_seconds()
        self.Comment = ("commenthidden" in data and "< Comment hidden >") or data["comment"]
        self.Size = data["size"]
        if type(diff) == int:
            self.SizeChange = diff
        else:
            self.SizeChange = self.Size
        self.IsMinor = "minor" in data
        self.IsIP = "anon" in data
        self.IsSuppressed = "suppressed" in data
    def IsMove(self):
        #Returns wasMoved, From, To
        #This will ignore move revisions that created a page by placing redirect categories (the page left behind)
        if self.SizeChange == 0:
            moveData = revisionMoveRegex.search(self.Comment)
            if moveData and moveData.group(1) == self.User:
                return True, moveData.group(2), moveData.group(3)
        return False, None, None

def CheckActionCount():
    global lastActionTime
    global actionCount
    if actionCount >= maxEdits and maxEdits > 0:
        lsucc(f"\n\nThe bot has hit its action count limit of {maxEdits} and will not make any further edits. Pausing script indefinitely...")
        while True:
            time.sleep(60)
    actionCount += 1
    if actionCount % 10 == 0:
        log(f"Action count: {actionCount}")
    if time.time()-lastActionTime < APS: #Slow it down
        print("Waiting for action cooldown to wear off")
        while time.time()-lastActionTime < APS:
            time.sleep(.2)
    lastActionTime = time.time()

bracketbalancereg = regex.compile('{{|}}') #For template processing
class Article: #Creates a class representation of an article to contain functions instead of calling them from everywhere. Also makes management easier
    def __init__(self, identifier):
        if type(identifier) == str:
            identifier = urllib.parse.quote(identifier.replace("_", " "))
            searchType = "titles"
        elif type(identifier) == int:
            searchType = "pageids"
        elif type(identifier) == dict and "pageid" in identifier:
            identifier = identifier["pageid"]
            searchType = "pageids"
        else:
            raise Exception(f"Invalid identifier in Article '{identifier}'")
        pageInfo = requestapi("get", f"action=query&prop=info&indexpageids=&intestactions=edit|move&{searchType}={identifier}")
        pageInfo = pageInfo["query"]["pages"][pageInfo["query"]["pageids"][0]] #Loooovely oneliner, ay?
        self.rawdata = pageInfo
        self.NamespaceID = pageInfo["ns"]
        self.Namespace = GetNamespace(self.NamespaceID)
        self.exists = not "missing" in pageInfo
        self.Title = pageInfo["title"]
        self.URLTitle = urllib.parse.quote(self.Title)
        self.IsRedirect = "redirect" in pageInfo
        self.CanEdit = "edit" in pageInfo["actions"]
        self.CanMove = "move" in pageInfo["actions"]
        if self.exists:
            self.PageID = pageInfo["pageid"]
            self.CurrentRevision = pageInfo["lastrevid"]
        #Storage variables
        self.Content = None
        self.Templates = None
    def __str__(self):
        return self.Title
    def GetContent(self):
        if not self.exists:
            return
        if self.Content != None:
            return self.Content
        if self.NamespaceID < 0:
            #Special pages do exist, but their content is, for our purposes, not relevant here.
            #For simplicity we just assign empty strings
            self.Content = ""
            return ""
        data = requestapi("get", f"action=query&prop=revisions&indexpageids=&pageids={self.PageID}&rvslots=*&rvprop=timestamp|user|comment|content")
        data = data["query"]["pages"][data["query"]["pageids"][0]]
        self.Content = data["revisions"][0]["slots"]["main"]["*"] #Idk man
        return self.Content
    def edit(self, newContent, editSummary, *, minorEdit=False, allowPageCreation=True, bypassExclusion=False, markAsBot=True):
        #Edit a page's content, replacing it with newContent
        if CheckIfStopped():
            return
        if not self.exists and not allowPageCreation:
            return lwarn(f"[Article] Refusing to edit article that doesnt exist ({self})")
        if not bypassExclusion and self.HasExclusion():
            #Its been requested we stay away, so we will
            return lwarn(f"[Article] Refusing to edit page that has exclusion blocked ({self})")
        if INDEV:
            if not (self.Namespace in ["User", "User talk"] and self.Title.find(username) > -1):
                #Not in bot's user space, and indev, so get out
                lwarn(f"[Article] Attempted to push edit to a space other than our own while in development mode ({self})")
                return False
            editSummary += ") (INDEV"
        if not SUBMITEDITS:
            #open(urllib.parse.quote(article).replace("/", "slash")+".txt", "w").write(newContent)
            return lwarn(f"[Article] Not submitting edit to {self} with summary '{editSummary}' as SUBMITEDITS is set to False")
        #All of our customary checks are done, now we actually start trying to edit the page
        CheckActionCount()
        log(f"Making edits to {self}:\n    {editSummary}")
        formData = {"pageid":self.PageID, "text":newContent, "summary":editSummary, "token":GetTokenForType("csrf"), "baserevid":self.CurrentRevision}
        if minorEdit:
            formData["minor"] = ""
        if markAsBot:
            formData["bot"] = ""
        if not allowPageCreation:
            formData["nocreate"] = ""
        try:
            return CreateAPIFormRequest("action=edit", formData)
        except Exception as exc:
            lerror(f"[Article edit] Warning: Failed to submit an edit request for {self} - {traceback.format_exc()}")
    def MoveTo(self, newPage, reason, *, leaveRedirect=True, bypassExclusion=False):
        #Move the page from its current location to a new one
        #Avoid supressing redirects unless necessary
        if CheckIfStopped():
            return
        if not bypassExclusion and self.HasExclusion():
            #Its been requested we stay away, so we will
            return lwarn(f"[Article] Refusing to move page that has us exclusion blocked ({self})")
        if INDEV:
            if not (self.Namespace in ["User", "User talk"] and self.Title.find(username) > -1):
                #Not in bot's user space, and indev, so get out
                return lwarn(f"[Article] Attempted to move a page in a space other than our own while in development mode ({self})")
            reason += ") (INDEV"
        if not SUBMITEDITS:
            return lwarn(f"[Article] Not moving {self} to {newPage} with summary '{reason}' as SUBMITEDITS is set to False")
        #All our customary checks are done, begin the process of actually moving
        CheckActionCount()
        log(f"Moving {self} to {newPage}{leaveRedirect==False and ' (Redirect supressed)' or ''}:\n    {reason}")
        formData = {"fromid":self.PageID, "to":newPage, "reason":reason, "token":GetTokenForType("csrf")}
        if not leaveRedirect:
            formData["noredirect"] = ""
        try:
            return CreateAPIFormRequest("action=move", formData)
        except Exception as exc:
            lerror(f"[Article move] Warning: Failed to submit a move request for {self} - {traceback.format_exc()}")
    def GetWikiLinks(self):
        if not self.exists:
            return []
        data = requestapi("get", f"action=query&prop=links&indexpageids=&pllimit=200&padeids={self.PageID}")
        data = data["query"]["pages"][data["query"]["pageids"][0]]
        return data["links"]
    def GetSubpages(self):
        return requestapi("get", f"action=query&list=prefixsearch&pslimit=100&pssearch={self.URLTitle}/")["query"]["prefixsearch"]
    def GetTemplates(self):
        if self.Templates != None:
            return self.Templates
        if not self.exists:
            return []
        templates = []
        textToScan = self.GetContent()
        while True:
            nextTemplate = textToScan.find("{{")
            if nextTemplate == -1:
                break #Found all templates, exit
            textToScan = textToScan[nextTemplate:]
            balance = 1
            furthestScan = 0
            while True:
                nextBracket = bracketbalancereg.search(textToScan[furthestScan+2:])
                if nextBracket:
                    bracketType = nextBracket.group()
                    balance += (bracketType == "{{" and 1) or -1
                    furthestScan += nextBracket.end()
                    if balance == 0:
                        templates.append(Template(textToScan[:furthestScan+2]))
                        textToScan = textToScan[2:] #Move past brackets
                        break
                else:
                    textToScan = textToScan[2:] #Skip past unbalanced bracket set
                    break #Unfinished template, ignore it
        self.Templates = templates
        verbose("Article", f"Registered {len(self.Templates)} templates for {self}")
        return self.Templates
    def GetLinkedPage(self):
        #Article gets Talk, Talk gets Article, you get the idea
        ID = self.NamespaceID
        if ID < 0: #Special pages have no talk
            return self
        elif ID == 1: #Special case for converting from Talk: to article space
            return Article(StripNamespace(self.Title))
        elif ID % 2 == 0:
            return Article(GetNamespace(ID+1) + ":" + StripNamespace(self.Title))
        else:
            return Article(GetNamespace(ID-1) + ":" + StripNamespace(self.Title))
    def GetHistory(self, limit=50, getContent=False):
        properties = "ids|timestamp|user|comment|flags|size"
        if getContent:
            properties += "|content"
        data = requestapi("get", f"action=query&prop=revisions&indexpageids=&pageids={self.PageID}&rvslots=*&rvlimit={limit}&rvprop={properties}")
        data = data["query"]["pages"][data["query"]["pageids"][0]]
        revisions = []
        for i in range(len(data["revisions"])):
            revision = data["revisions"][i]
            if i != len(data["revisions"])-1:
                child = data["revisions"][i+1]
                revisions.append(Revision(revision, revision["size"] - child["size"]))
            else:
                revisions.append(Revision(revision))
        return revisions
    def HasExclusion(self):
        #If the bot is excluded from editing a page, this returns True
        if not self.exists:
            return False
        for template in self.GetTemplates():
            if template.Template.lower() == "nobots": #We just arent allowed here
                log("[Article] nobots presence found")
                return True
            if template.Template.lower() == "bots": #Check |deny= and |allow=
                if "allow" in template.Args:
                    for bot in template.Args["allow"].split(","):
                        bot = bot.lower().strip()
                        if bot == username.lower() or bot == "all": #Allowed all or specific
                            log("[Article] {{bots}} presence found but permitted")
                            return False
                    log("[Article] {{bots}} presence found, not permitted")
                    return True #Not in the "allowed" list, therefore we dont get to be here
                if "deny" in template.Args:
                    for bot in template.Args["deny"].split(","):
                        bot = bot.lower().strip()
                        if bot == username.lower() or bot == "all": #Banned all or specific
                            log("[Article] {{bots}} presence found, denied")
                            return True
                        if bot == "none": #Allow all
                            log("[Article] {{bots}} presence found, not denied")
                            return False
                log("[Article] Exclusion check has managed to not hit a return, which is very odd")

def IterateCategory(category, torun):
    #Iterates all wikilinks of a category, even if multi-paged
    CheckIfStopped()
    catpage = Article(category)
    if not catpage.exists:
        return lalert(f"[IterateCategory] Attempted to iterate '{category}' despite it not existing")
    data = requestapi("get", f"action=query&list=categorymembers&cmtype=page&cmlimit=100&cmpageid={catpage.PageID}")
    for page in data["query"]["categorymembers"]:
        torun(Article(page["pageid"]))
    cmcontinue = "continue" in data and data["continue"]["cmcontinue"]
    while cmcontinue:
        CheckIfStopped()
        data = requestapi("get", f"action=query&list=categorymembers&cmtype=page&cmlimit=100&cmpageid={catpage.PageID}&cmcontinue={cmcontinue}")
        for page in data["query"]["categorymembers"]:
            torun(Article(page["pageid"]))
        cmcontinue = "continue" in data and data["continue"]["cmcontinue"]

class WikiConfig: #Handles the fetching of configs from on-wiki locations
    def __init__(self, page, defaultConfig):
        self.Page = page
        self.Config = defaultConfig
    def update(self):
        Page = Article(self.Page)
        if not Page.exists:
            return lalert(f"[WikiConfig] Page {self.Page} doesn't exist")
        else:
            try:
                NewConfig = json.loads(Page.GetContent())
            except Exception as exc:
                return lerror(f"[WikiConfig] Trouble parsing {self.Page}: {exc}")
            else:
                for key,data in NewConfig.items():
                    value = data["Value"]
                    if self.Config[key] != value:
                        log(f"[WikiConfig] '{key}' in config {self.Page} was changed to '{value}'")
                        self.Config[key] = value
    def get(self, key):
        if key in self.Config:
            return self.Config[key]
        return None


username, userid = None, None
def AttemptLogin(name, password):
    global username, userid
    log(f"Attempting to log-in as {name}")
    loginAttempt = CreateAPIFormRequest("action=login", {"lgname":name, "lgpassword":password, "lgtoken":GetTokenForType("login")})["login"]
    #TODO: Move away from the deprecated "login" and towards "clientlogin"
    #TODO: Consider adapting botpass instead of straight logging to allow stricter control
    if loginAttempt["result"] != "Success":
        lerror(f"Failed to log-in as {name}. check the password and username are correct")
        return False, None
    else:
        username = loginAttempt["lgusername"]
        userid = loginAttempt["lguserid"]
        lsucc(f"Successfully logged in as {username} (ID {userid})")
        return True, username
log("WikiTools has loaded")
