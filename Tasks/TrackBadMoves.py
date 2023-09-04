#This task tracks Special:Log/move, watching for any moves that appear to have left a subpage improperly orphaned

from wikitools import *
import re as regex
import datetime
import time
import math

Config = WikiConfig(f"User:{username}/TrackBadMoves/config", {
    "CheckBufferTime": 10
})

PagesToCheck = []
PagesToFlag = []
CheckedLogs = set()

def DetermineIfMoveIsPoor(oldpage, newpage):
    OldPage = Article(oldpage)
    NewPage = Article(newpage)
    if not NewPage.Exists:
        return False, 2
    if not NewPage.GetLinkedPage().Exists: #Confusing move, dont touch
        return False, 3
    if not OldPage.IsRedirect: #Move reverted in some way
        return False, 4
    OldSubpages = OldPage.GetSubpages()
    if len(OldSubpages) > 0:
        log(f"Considering {len(OldSubpages)} subpages for {OldPage}")
        NonRedirects = []
        for subpage in OldSubpages:
            subpageobj = Article(subpage)
            if not subpageobj.IsRedirect and not subpageobj.GetLinkedPage().Exists:
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
    #We do it this way to allow a human to essentially intervene and manually declare/undeclare a move as poor
    FlaggedPages = GatherExistingEntries()
    FlaggedPages.extend(PagesToFlag)
    seenPages = []
    for page in list(FlaggedPages):
        logid = page["logid"]
        if logid in seenPages:
            FlaggedPages.remove(page)
        else:
            seenPages.append(logid)
    pagesDropped = 0
    for page in list(FlaggedPages):
        IsPoor, Data = DetermineIfMoveIsPoor(page["oldpage"], page["newpage"])
        if not IsPoor:
            pagesDropped += 1
            FlaggedPages.remove(page)
    pagesAdded = len(PagesToFlag)
    pagesPastCheck = len(FlaggedPages)
    PagesToFlag = []

    output = ""
    for page in FlaggedPages:
        oldpage   = page['oldpage']
        newpage   = page['newpage']
        subpages  = str(page['subpages'])
        logtime   = str(datetime.datetime.fromtimestamp(page['logtime']))
        logid     = str(page['logid'])
        output = output + f"|-\n{{{{/entry|oldpage={oldpage}|newpage={newpage}|subpages={subpages}|logtime={logtime}|logid={logid}}}}}\n"
    output = output + "|}"
    editMarker = "<!-- Bot Edit Marker -->"
    reportPage = Article(f"User:{username}/TrackBadMoves/report")
    existingContent = reportPage.GetContent()
    if existingContent.find(editMarker) == -1:
        headerText = editMarker+"\n"
    else:
        headerText = existingContent[:existingContent.find(editMarker)+len(editMarker)+1]

    editSummary = "Update report"
    if pagesPastCheck == 1:
        editSummary += " (1 entry)"
    else:
        editSummary += f" ({pagesPastCheck} entries)"
    if pagesDropped == 1:
        editSummary += " | 1 page removed"
    elif pagesDropped > 1:
        editSummary += f" | {pagesDropped} pages removed"
    if pagesAdded == 1:
        editSummary += " | 1 page added"
    elif pagesAdded > 1:
        editSummary += f" | {pagesAdded} pages added"

    reportPage.Edit(headerText+output, editSummary)

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
                    "logtime":datetime.datetime.fromisoformat(event["timestamp"][:-1]).timestamp()
                })

    for page in list(PagesToCheck):
        if datetime.datetime.utcnow().timestamp() > page["logtime"] + 60*Config.get("CheckBufferTime"):
            IsPoor, Data = DetermineIfMoveIsPoor(page["oldpage"], page["newpage"])
            if IsPoor:
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
                for key in ["logtime"]:
                    entry[key] = math.floor(datetime.datetime.fromisoformat(template.Args[key]).timestamp())
            except Exception as exc:
                lwarn(f"Unable to parse line '{line}' - {exc}")
            else:
                entries.append(entry)
    log(f"Managed to parse {len(entries)} entries")
    return entries


def __main__():
    prevMinute = datetime.datetime.utcnow().minute
    prevHour = datetime.datetime.utcnow().hour
    while True:
        curMinute = datetime.datetime.utcnow().minute
        curHour = datetime.datetime.utcnow().hour
        if HaltIfStopped():
            prevMinute = datetime.datetime.utcnow().minute
            prevHour = datetime.datetime.utcnow().hour
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
