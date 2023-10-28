#This task tracks Special:Log/move, watching for any moves that appear to have left a subpage improperly orphaned, and fixes them automatically

from wikitools import *
import datetime
import time
import math

username, userid = GetSelf()

Config = WikiConfig(f"User:{username}/FixBadMoves/config", {
    "CheckBufferTime": 10,
    "SubpageMoveLimit": 15,
    "DaysUntilFix": 7,
})

PagesToCheck = []
PagesToFlag = []
CheckedLogs = set()

WILL_FIX = 1 # All normal, will be automatically fixed
WONT_FIX = 2 # Fine technically, but something seems off - divert to a human
CANT_FIX = 3 # Technical issue preventing a fix entirely
IS_FIXED = 4 # Nothing to do here

def CalculateSubpageFixability(OldPage, NewPage):
    OldSubpages = OldPage.GetSubpages()
    if len(OldSubpages) > 0:
        if not OldPage.IsRedirect:
            if (NewPage.IsRedirect and Article(NewPage.PageID, FollowRedirects=True).PageID == OldPage.PageID) or not NewPage.Exists:
                return IS_FIXED, "The move was reverted"
            return WONT_FIX, "The old page is no longer a redirect"
        if NewPage.IsRedirect:
            return WONT_FIX, "The new page is now also a redirect"
        if not (OldPage.GetLinkedPage().Exists and NewPage.GetLinkedPage().Exists):
            return WONT_FIX, "One of the pages is missing an associated article page?"
        success, result = NewPage.CanEditWithConditions()
        if not success:
            return CANT_FIX, "The new page target can't be edited"
        PagesToBeMoved = []
        for Subpage in OldSubpages:
            Subpage = Article(Subpage)
            if Subpage.GetLinkedPage().Exists:
                return WONT_FIX, "One of the subpages has a linked article page"
            if not Subpage.IsRedirect:
                PagesToBeMoved.append(Subpage)
        if len(PagesToBeMoved) > 0:
            if len(PagesToBeMoved) > Config.get("SubpageMoveLimit"):
                return WONT_FIX, "There are a non-trivial amount of subpages to be moved"
            FixMap = {}
            for Subpage in PagesToBeMoved:
                NewName = NewPage.Title+Subpage.Title[len(OldPage.Title):]
                success, result = Subpage.CanMoveTo(NewName)
                if not success:
                    return CANT_FIX, "Can't move [[" + Subpage.Title + "]] to [[" + NewName + "]]"
                else:
                    FixMap[Subpage] = NewName
            return WILL_FIX, FixMap
    return IS_FIXED, "There are no non-redirect subpages"


def FixPageTemplates(OldPage, NewPage):
    Templates = NewPage.GetTemplates()
    HadAChange = False
    Content = NewPage.GetContent()
    for Template in Templates:
        TemplateName = Template.Template

        if TemplateName.lower() == "user:miszabot/config":
            #Fix for MiszaBot / Lowercase Sigmabot III
            if "archive" in Template.Args:
                archive = Template.Args["archive"]
                if archive.startswith(OldPage.Title + "/"):
                    # fixable
                    Template.ChangeKeyData("archive", archive.replace(OldPage.Title + "/", NewPage.Title + "/"))
                    Content = Content.replace(Template.Original, Template.Text)
                elif not archive.startswith(NewPage.Title + "/"):
                    # neither the previous nor current page, just give up, needs human attention
                    return WONT_FIX, "User:MiszaBot/config"
                #else: already fixed, whatever
            else: #uh... what?
                return WONT_FIX, "User:MiszaBot/config"

        elif TemplateName.lower() == "user:hbc archive indexerbot/optin":
            #Fix for Legobot
            if "target" in Template.Args and "mask" in Template.Args:
                if "mask1" in Template.Args:
                    return WONT_FIX, "User:HBC Archive Indexerbot/OptIn" #too complex a situation for us (im lazy), dont touch it
                target, mask = Template.Args["target"], Template.Args["mask"]
                if target.startswith(OldPage.Title + "/") and mask.startswith(OldPage.Title + "/"):
                    # fixable
                    Template.ChangeKeyData("target", target.replace(OldPage.Title + "/", NewPage.Title + "/"))
                    Template.ChangeKeyData("mask", mask.replace(OldPage.Title + "/", NewPage.Title + "/"))
                    Content = Content.replace(Template.Original, Template.Text)
                elif not(target.startswith(NewPage.Title + "/") and mask.startswith(NewPage.Title + "/")):
                    # neither the previous nor current page, just give up, needs human attention
                    return WONT_FIX, "User:HBC Archive Indexerbot/OptIn"
            else: #more missing required arguments
                return WONT_FIX, "User:HBC Archive Indexerbot/OptIn"

        elif TemplateName.lower() == "user:cluebot iii/archivethis":
            #Fix for ClueBot III
            if "archiveprefix" in Template.Args:
                archiveprefix = Template.Args["archiveprefix"]
                if archiveprefix.startswith(OldPage.Title + "/"):
                    # fixable
                    Template.ChangeKeyData("archiveprefix", archiveprefix.replace(OldPage.Title + "/", NewPage.Title + "/"))
                    Content = Content.replace(Template.Original, Template.Text)
                elif not archiveprefix.startswith(NewPage.Title + "/"):
                    # neither the previous nor current page, just give up, needs human attention
                    return WONT_FIX, "User:ClueBot III/ArchiveThis"
            else: #these args are needed! stop missing them!!
                return WONT_FIX, "User:ClueBot III/ArchiveThis"

    if Content != NewPage.GetContent():
        return WILL_FIX, Content
    else:
        return IS_FIXED, Content


def ConsiderFixingPages(PageSet):
    BadPages = []
    for item in list(PageSet):
        MoveData, PendingMoves = item #magical python unpacking
        OldPage = MoveData["oldpage_article"]
        NewPage = MoveData["newpage_article"]
        Status, NewContent = FixPageTemplates(OldPage, NewPage)
        if Status == WONT_FIX or Status == CANT_FIX:
            # Template sorting has gone wrong, dont continue further!
            lwarn(f"{item[0]} has got some template issues")
            PageSet.remove(item)
            BadPages.append([item[0], "Issue during template handling with " + str(NewContent)])
            continue
        # Check how long its been
        if datetime.datetime.utcnow().timestamp() > MoveData["logtime"] + 86400*Config.get("DaysUntilFix"):
            # Handle the subpages
            for OldSubpage, NewSubpage in PendingMoves.items():
                OldSubpage.MoveTo(NewSubpage, f"Move subpage left behind during move of parent page ([[User talk:{username}|Report bot issues]])", checkTarget=False) #already checked target
            # And then apply template fixes
            if Status == WILL_FIX:
                log(f"Fixing {MoveData['oldpage']} required editing some templates")
                NewPage.Edit(NewContent, f"Update archiving templates after a page move ([[User talk:{username}|Report bot issues]])")
            PageSet.remove(item)
        else:
            pass # Just hold on a bit, dont fix it just yet
    return BadPages


def PostRelevantUpdates():
    global PagesToFlag
    #We do it this way to allow a human to essentially intervene and manually declare/undeclare a move as poor
    FlaggedPages = GatherExistingEntries()
    FlaggedPages.extend(PagesToFlag)
    PagesToFlag = []
    seenPages = []
    for page in list(FlaggedPages):
        newpage = page["newpage"]
        if newpage in seenPages:
            FlaggedPages.remove(page)
        else:
            seenPages.append(newpage)

    Pages_willfix = []
    Pages_wontfix = []
    Pages_cantfix = []
    log("Calculating the fixability of pages...")
    for page in list(FlaggedPages):
        OldPage, NewPage = Article(page["oldpage"]), Article(page["newpage"])
        page["oldpage_article"] = OldPage
        page["newpage_article"] = NewPage
        Decision, Data = CalculateSubpageFixability(OldPage, NewPage)
        # print(page, Decision, Data)
        if Decision == IS_FIXED:
            FlaggedPages.remove(page)
        elif Decision == WILL_FIX:
            Pages_willfix.append([page, Data])
        elif Decision == WONT_FIX:
            lwarn(f"Refused to automatically fix {OldPage} because {Data}")
            Pages_wontfix.append([page, Data])
        elif Decision == CANT_FIX:
            lwarn(f"Unable to automatically fix {OldPage} because {Data}")
            Pages_cantfix.append([page, Data])

    log("Attempting to fix some of the fixable pages...")
    BadPages = ConsiderFixingPages(Pages_willfix)
    Pages_wontfix.extend(BadPages)

    output = "|-\n! colspan=6 | To be automatically fixed\n"
    for item in Pages_willfix:
        page = item[0]
        oldpage  = page['oldpage']
        newpage  = page['newpage']
        subpages = str(page['subpages'])
        logtime  = str(datetime.datetime.fromtimestamp(page['logtime']))
        output = output + f"|-\n{{{{/entry|oldpage={oldpage}|newpage={newpage}|subpages={subpages}|logtime={logtime}|problem=}}}}\n"
    output = output + "|-\n! colspan=6 | Requires human attention\n"
    for item in Pages_wontfix:
        page = item[0]
        oldpage  = page['oldpage']
        newpage  = page['newpage']
        subpages = str(page['subpages'])
        logtime  = str(datetime.datetime.fromtimestamp(page['logtime']))
        problem  = item[1]
        output = output + f"|-\n{{{{/entry|oldpage={oldpage}|newpage={newpage}|subpages={subpages}|logtime={logtime}|problem={problem}}}}}\n"
    output = output + "|-\n! colspan=6 | Can't automatically fix\n"
    for item in Pages_cantfix:
        page = item[0]
        oldpage  = page['oldpage']
        newpage  = page['newpage']
        subpages = str(page['subpages'])
        logtime  = str(datetime.datetime.fromtimestamp(page['logtime']))
        problem  = item[1]
        output = output + f"|-\n{{{{/entry|oldpage={oldpage}|newpage={newpage}|subpages={subpages}|logtime={logtime}|problem={problem}}}}}\n"
    output = output + "|}"
    editMarker = "<!-- Bot Edit Marker -->"
    reportPage = Article(f"User:{username}/FixBadMoves/report")
    existingContent = reportPage.GetContent()
    if existingContent.find(editMarker) == -1:
        headerText = editMarker+"\n"
    else:
        headerText = existingContent[:existingContent.find(editMarker)+len(editMarker)+1]

    editSummary = f"Update report | {len(Pages_willfix) + len(Pages_wontfix) + len(Pages_cantfix)} entries"

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
            result, message = CalculateSubpageFixability(Article(OldPage), Article(NewPage))
            if result != IS_FIXED:
                log(f"'{OldPage}' is now in the buffer check")
                PagesToBeMoved = []
                for Subpage in Article(OldPage).GetSubpages():
                    Subpage = Article(Subpage)
                    if not Subpage.IsRedirect:
                        PagesToBeMoved.append(Subpage)
                PagesToCheck.append({
                    "oldpage":OldPage, "newpage":NewPage, "subpages":len(PagesToBeMoved),
                    "logtime":datetime.datetime.fromisoformat(event["timestamp"][:-1]).timestamp()
                })

    for page in list(PagesToCheck):
        if datetime.datetime.utcnow().timestamp() > page["logtime"] + 60*Config.get("CheckBufferTime"):
            result, message = CalculateSubpageFixability(Article(page["oldpage"]), Article(page["newpage"]))
            if result != IS_FIXED:
                lwarn(f"{page['oldpage']} has failed the buffer check, and has now moved to the flagged list")
                PagesToFlag.append(page)
            PagesToCheck.remove(page)


def GatherExistingEntries():
    entries = []
    log("Attempting to parse existing entries...")
    reportPage = Article(f"User:{username}/FixBadMoves/report")
    content = reportPage.GetContent()
    for line in content.split("\n"):
        if line.startswith("{{/entry") and line.endswith("}}"):
            try:
                template = Template(line)
                entry = {}
                for key in ["oldpage", "newpage"]:
                    entry[key] = template.Args[key]
                for key in ["subpages"]:
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
        elif curHour != prevHour and curHour%12 == 0:
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
        prevMinute = curMinute
        prevHour = curHour
