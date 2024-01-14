#This task fixes the archive parameter for the {{User:MiszaBot/config}} template, as well as the position of left-behind subpages

from wikitools import *
import re as regex
import traceback
import datetime
import time

username, userid = GetSelf()

Config = WikiConfig(f"User:{username}/FixArchiveLocations/config", {
    "MoveWarLimit": 3,
    "MoveWarTimeLimit": 28,
    "MoveCheckTimeLimit": 7,
    "TimeUntilMoveAction": 12
})

unsafeCases = {}
archiveTemplates = regex.compile("^[Uu]ser:([Mm]iszaBot|[Ll]owercase sigmabot III)/config")
def MarkUnsafe(title, reason):
    global unsafeCases
    log(f"Just placed {title} on the no-action list: {reason}")
    unsafeCases[title] = reason
def DetermineBadMove(page):
    #Attempts to determine if pages from before weren't moved under the new name
    currentLocation = page.Title
    recentMoves = 0

    revisions = page.GetHistory(200)
    #Avoid editing if the page has received a mass amount of recent moves
    for revision in revisions:
        wasMoved, From, To = revision.IsMove()
        if wasMoved and revision.Age < 86400*Config.get("MoveWarTimeLimit"):
            recentMoves += 1
            if recentMoves >= Config.get("MoveWarLimit"):
                return MarkUnsafe(currentLocation, f"Page could be undergoing a move war ({recentMoves} recent moves), not participating")

    #Otherwise, scan the history
    #The script checks only the most recent move, and no further
    for revision in revisions:
        wasMoved, From, To = revision.IsMove()
        if wasMoved and revision.Age < 86400*Config.get("MoveCheckTimeLimit"):
            log(f"Examining the move from {revision.Timestamp} by {revision.User}")
            prevPage = Article(From)
            if not prevPage.Exists:
                return MarkUnsafe(currentLocation, "Origin page of the move doesn't exist")

            #At this point, we should be happy enough to go ahead and move pages
            subpages = prevPage.GetSubpages()
            if len(subpages) == 0:
                return MarkUnsafe(currentLocation, "Couldn't find any pages to move")
            articleSubpages = []
            for subpage in subpages:
                subpage = Article(subpage)
                if not subpage.IsRedirect:
                    articleSubpages.append(subpage) #Avoid double-grabbing
            if len(articleSubpages) == 0:
                return MarkUnsafe(currentLocation, "All of the pages under the previous title are redirects themselves..?")

            #Verify all subpages are movable within reason
            for subpage in articleSubpages:
                if not subpage.Title.startswith(prevPage.Title+"/Archive"):
                    #If the page is not an archive, to avoid the "Subpage of A/B listed under A" situation, ensure the page doesnt have a non-talk version
                    if subpage.GetLinkedPage().Exists:
                        return MarkUnsafe(currentLocation, "Some subpages didn't meet the move criteria")
                newLocation = currentLocation+subpage.Title[len(prevPage.Title):]
                success, result = subpage.CanMoveTo(newLocation)
                if not success:
                    #If we can't move one of the subpages for any reason (titleblacklist, protection, etc.), dont move any
                    return MarkUnsafe(currentLocation, f"At least one subpage can't be moved: {result}")

            #All cool, go ahead and move (just make sure it happened a bit ago)
            if revision.Age < 3600*Config.get("TimeUntilMoveAction"):
                log("Move was too recent, avoiding fixing it just yet")
                return #Don't alert help page for this
            else:
                # for subpage in articleSubpages:
                #     subpage.MoveTo(
                #         currentLocation+subpage.Title[len(prevPage.Title):],
                #         "Relocating subpage under new page title"
                #     ) #Move to new page with subpage suffix kept
                return len(subpages)

    MarkUnsafe(currentLocation, "No recent enough page moves found")

def CheckArchiveLocations(page):
    content = page.GetContent()
    currentLocation = page.Title
    extraNote = ""
    for template in page.GetTemplates(): #Will only fix the first template occurance, and not any more
        if archiveTemplates.search(template.Template):
            if "archive" in template.Args and (not "key" in template.Args or template.Args["key"].strip() == ""):
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location, as well as cleaning up any issues left behind
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(?:/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee] %\(counter\)d)").search(archiveLocation) #For simplicity, only deal with %(counter)d
                    if existingArchive:
                        #Lets just make sure it's not bot blocked
                        if page.HasExclusion():
                            return MarkUnsafe(currentLocation, "The bot cleared the initial GIGO checks, but is excluded from the target page")
                        wantedLocation = existingArchive.group()
                        if wantedLocation[0] == "/": #Stupid but eh
                            newArchive = currentLocation+wantedLocation
                        else:
                            newArchive = currentLocation+"/"+wantedLocation

                        #Verify this archive is valid by checking if it exists
                        archivePage = Article(newArchive.replace(r"%(counter)d", "1"))
                        if not archivePage.Exists or archivePage.IsRedirect:
                            #At this point, we attempt to move pages from the old name, in case the mover just happened to forget
                            log(f"{currentLocation} failed safety check (Missing expected archives), checking previous pages")
                            DetermineBadMove(page)
                            # Page moving functionality has been disabled as Task 3 is now responsible for this

                        else: #Archive exists under the page already, fixes can go ahead
                            lsucc("[Archive Fix] Safety test has been passed")
                            template.ChangeKeyData("archive", newArchive)
                            content = content.replace(template.Original, template.Text)
                    else: #Regex did not match
                        MarkUnsafe(currentLocation, "Couldn't find a supported archive value")
                else: #Value passed the test and shouldn't be considered faulty
                    MarkUnsafe(currentLocation, "The archive value is fine, but it's still in the category")
            elif not "archive" in template.Args: #No archive key
                MarkUnsafe(currentLocation, "No archive key present")
            break
    if content != page.GetContent():
        page.Edit(content, f"Fixed archive location for Lowercase Sigmabot III{extraNote} ([[User:MiszaBot/config#Parameters explained|More info]] - [[User talk:{username}|Report bot issues]])", minorEdit=True)

def __main__():
    # CheckArchiveLocations(Article(f"User:{username}/encoded–title"))
    prevHour = datetime.datetime.utcnow().hour #Hourly checks
    while True:
        curHour = datetime.datetime.utcnow().hour
        if HaltIfStopped():
            prevHour = datetime.datetime.utcnow().hour
        elif curHour != prevHour:
            prevHour = curHour
            log("Beginning cycle")
            Config.update()
            try:
                IterateCategory("Category:Pages where archive parameter is not a subpage", CheckArchiveLocations)
            except Exception as exc:
                lerror(f"Encountered a problem while trying to iterate the category: {traceback.format_exc()}")
            else:
                log("Finished cycle")
                if len(unsafeCases) == 0:
                    Article(f"User:{username}/FixArchiveLocations/report").Edit("No problems", "[Task 2] No problems")
                else:
                    problematicList = ""
                    for page, reason in unsafeCases.items():
                        problematicList += f"\n* [[:{page}]] - {reason}"
                    Article(f"User:{username}/FixArchiveLocations/report").Edit(f"Encountered some issues with archives on the following pages:{problematicList}", f"[Task 2] Requesting help on {len(unsafeCases)} page(s)")
            unsafeCases.clear()
        else:
            time.sleep(1)