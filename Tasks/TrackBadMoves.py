#This task tracks Special:Log/move, watching for any moves that appear to have left a subpage improperly orphaned

from wikitools import *
import re as regex
import datetime
import time
import math

Config = WikiConfig(f"User:{username}/TrackBadMoves/config", {
    "CheckBufferTime": 10,
    "RecheckTime": 2,
    "TimeUntilSlowRecheck": 24,
    "SlowRecheckTime": 12,
})

PagesToCheck = []
PagesToFlag = []
CheckedLogs = set()

def DetermineIfMoveIsPoor(oldpage, newpage):
    OldPage = Article(oldpage)
    NewPage = Article(newpage)
    if not NewPage.exists:
        return False, 2
    if not NewPage.GetLinkedPage().exists: #Confusing move, dont touch
        return False, 3
    if NewPage.IsRedirect or not OldPage.IsRedirect: #Move reverted in some way
        return False, 4
    OldSubpages = OldPage.GetSubpages()
    if len(OldSubpages) > 0:
        log(f"Considering {len(OldSubpages)} subpages for {OldPage}")
        NonRedirects = []
        for subpage in OldSubpages:
            subpageobj = Article(subpage)
            if not subpageobj.IsRedirect and not subpageobj.GetLinkedPage().exists:
                NonRedirects.append(subpageobj)
        if len(NonRedirects) > 0: #At least 1 non-redirect page left behind
            for subpage in NewPage.GetSubpages():
                subpageobj = Article(subpage)
                if not subpageobj.IsRedirect:
                    return False, 5 #New target has a non-redirect subpage. Assume it's fine
            return True, NonRedirects #Considered unfinished
        else:
            return False, 1
    else:
        return False, 1 #No subpages under old title
    return False, -1 #Should not reach

def CreateSortableDate(datetime):
    #Unused but kept for testing
    return f'data-sort-value="{datetime.year} {datetime.month} {datetime.day}"|{datetime}'

def PostRelevantUpdates():
    global PagesToFlag
    FlaggedPages = GatherExistingEntries()
    FlaggedPages.extend(PagesToFlag)
    #We do it this way to allow a human to essentially intervene and manually declare/undeclare a move as poor
    PagesToFlag = []
    pagesDropped = 0
    pagesKept = 0
    pagesUnchecked = 0
    for page in list(FlaggedPages):
        curTimestamp = math.floor(datetime.datetime.now().timestamp())
        if curTimestamp > page["logtime"] + 3600*Config.get("TimeUntilSlowRecheck"):
            waitTime = 3600*Config.get("SlowRecheckTime")
        else:
            waitTime = 3600*Config.get("RecheckTime")
        if curTimestamp > page["checktime"] + waitTime-300: #5m offset to avoid stupid off-by-1-second cases
            IsPoor, Data = DetermineIfMoveIsPoor(page["oldpage"], page["newpage"])
            if not IsPoor:
                pagesDropped += 1
                FlaggedPages.remove(page)
            else:
                pagesKept += 1
            page["checktime"] = curTimestamp
        else:
            pagesUnchecked += 1

    output = ""
    for page in FlaggedPages:
        oldpage   = page['oldpage']
        newpage   = page['newpage']
        subpages  = str(page['subpages'])
        logtime   = str(datetime.datetime.fromtimestamp(page['logtime']))
        logid     = str(page['logid'])
        checktime = str(datetime.datetime.fromtimestamp(page['checktime']))
        output = output + f"|-\n{{{{/entry|oldpage={oldpage}|newpage={newpage}|subpages={subpages}|logtime={logtime}|logid={logid}|checktime={checktime}}}}}\n"
    output = output + "|}"
    editMarker = "<!-- Bot Edit Marker -->"
    reportPage = Article(f"User:{username}/TrackBadMoves/report")
    existingContent = reportPage.GetContent()
    if existingContent.find(editMarker) == -1:
        headerText = editMarker+"\n"
    else:
        headerText = existingContent[:existingContent.find(editMarker)+len(editMarker)+1]

    editSummary = "Update report"
    if pagesDropped == 1:
        editSummary += " | 1 page removed"
    elif pagesDropped > 1:
        editSummary += f" | {pagesDropped} pages removed"
    if pagesKept == 1:
        editSummary += " | 1 page checked"
    elif pagesKept > 1:
        editSummary += f" | {pagesKept} pages checked"
    if pagesUnchecked == 1:
        editSummary += " | 1 page unchecked"
    elif pagesUnchecked > 1:
        editSummary += f" | {pagesUnchecked} pages unchecked"

    reportPage.edit(headerText+output, editSummary)

def PerformLogCheck():
    global PagesToCheck
    global PagesToFlag
    global CheckedLogs
    #The above globals aren't required but it's easier to understand this way

    LogData = requestapi("get", "action=query&list=logevents&letype=move&lelimit=50&lenamespace=1")
    LogEvents = LogData["query"]["logevents"]
    for event in LogEvents:
        if event["logid"] not in CheckedLogs:
            CheckedLogs.add(event["logid"])
            OldPage, NewPage = event["title"], event["params"]["target_title"]
            IsPoor, Data = DetermineIfMoveIsPoor(OldPage, NewPage)
            if IsPoor:
                log(f"'{OldPage}' is now in the buffer check")
                PagesToCheck.append({
                    "oldpage":OldPage, "newpage":NewPage, "subpages":len(Data), "logid":event["logid"],
                    "logtime":datetime.datetime.fromisoformat(event["timestamp"][:-1]).timestamp(),
                    "checktime":math.floor(datetime.datetime.now().timestamp()),
                })

    for page in list(PagesToCheck):
        if datetime.datetime.now().timestamp() > page["logtime"] + 60*Config.get("CheckBufferTime"):
            IsPoor, Data = DetermineIfMoveIsPoor(page["oldpage"], page["newpage"])
            if IsPoor:
                page["checktime"] = math.floor(datetime.datetime.now().timestamp())
                lwarn(f"{page['oldpage']} has failed the buffer check, and has now moved to the flagged list")
                PagesToFlag.append(page)
            PagesToCheck.remove(page)

def GatherExistingEntries():
    entries = []
    log("Attempting to parse existing entries...")
    reportPage = Article(f"User:{username}/TrackBadMoves/report")
    content = reportPage.GetContent()
    for line in content.split("\n"):
        if line.startswith("{{/entry") and line.endswith("}}"):
            try:
                template = Template(line)
                entry = {}
                for key in ["oldpage", "newpage"]:
                    entry[key] = template.Args[key]
                for key in ["subpages", "logid"]:
                    entry[key] = int(template.Args[key])
                for key in ["logtime", "checktime"]:
                    entry[key] = math.floor(datetime.datetime.fromisoformat(template.Args[key]).timestamp())
            except Exception as exc:
                lwarn(f"Unable to parse line '{line}' - {exc}")
            else:
                entries.append(entry)
    log(f"Managed to parse {len(entries)} entries")
    return entries


def __main__():
    prevMinute = datetime.datetime.now().minute
    prevHour = datetime.datetime.now().hour
    while True:
        curMinute = datetime.datetime.now().minute
        curHour = datetime.datetime.now().hour
        if HaltIfStopped():
            prevMinute = datetime.datetime.now().minute
            prevHour = datetime.datetime.now().hour
        elif curHour != prevHour:
            prevMinute = curMinute
            prevHour = curHour
            Config.update()
            log("Beginning hourly cycle")
            PerformLogCheck()
            PostRelevantUpdates()
            log("Finishing hourly cycle")
        elif curMinute != prevMinute:
            prevMinute = curMinute
            Config.update()
            PerformLogCheck()
        else:
            time.sleep(1)
