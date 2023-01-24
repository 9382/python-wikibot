#This task fixes the archive parameter for the {{User:MiszaBot/config}} template as well as other small factors

unsafeCases = {}
archiveTemplates = regex.compile("[Uu]ser:([Mm]iszaBot|[Ll]owercase sigmabot III)/config")
def DetermineBadMove(page):
    global unsafeCases
    #Attempts to determine if pages from before weren't moved under the new name
    currentLocation = page.Title
    recentMoves = 0

    #Avoid editing if the page has received a mass amount of recent moves
    for revision in page.GetHistory(30):
        wasMoved, From, To = revision.IsMove()
        if wasMoved and (datetime.datetime.now() - revision.Date).seconds < 86400*21: #3 weeks
            recentMoves += 1
    if recentMoves >= 3:
        unsafeCases[currentLocation] = f"Page could be undergoing a move war ({recentMoves} recent moves), not participating"
        return

    #Otherwise, scan the history
    #The script checks only the most recent move, and no further
    for revision in page.GetHistory(10):
        wasMoved, From, To = revision.IsMove()
        if wasMoved:
            verbose("Archive Fix", f"Examining the move from {revision.Timestamp} by {revision.User}")
            prevPage = Article(From)
            if not prevPage.exists:
                lwarn("[FixArchiveLocation] Previous page doesn't exist, that isn't right")
                unsafeCases[currentLocation] = "Origin page of the move doesn't exist"
            #At this point, we should be happy enough to go ahead and move pages
            subpages = prevPage.GetSubpages()
            if len(subpages) == 0:
                unsafeCases[currentLocation] = "Couldn't find any pages to move"
                return
            articleSubpages = []
            for subpage in subpages:
                articleSubpages.append(Article(subpage)) #Avoid double-grabbing
            #Verify all subpages are movable within reason
            for subpage in articleSubpages:
                if not subpage.Title.startswith(prevPage.Title+"/Archive"):
                    #If the page is not an archive, to avoid the "A/B/Subpage listed under A" situation, ensure the page doesnt have a non-talk version
                    if subpage.GetLinkedPage().exists:
                        unsafeCases[currentLocation] = "Some subpages didn't meet the automove criteria"
                        return
            #All cool, go ahead and move (just make sure it happened a bit ago)
            if (datetime.datetime.now() - revision.Date).seconds < 3600*6: #6 hours
                log("[FixArchiveLocation] Move was too recent, avoiding fixing it just yet")
                #unsafeCases[currentLocation] = "Move was too recent, not fixing it yet" #Dont alert help page just yet
                return
            else:
                for subpage in articleSubpages:
                    subpage.MoveTo(
                        currentLocation+subpage.Title[len(prevPage.Title):],
                        "Re-locating subpage under new page title"
                    ) #Move to new page with subpage suffix kept
                return len(articleSubpages)
    unsafeCases[currentLocation] = "No recent enough page moves found"

def CheckArchiveLocations(page):
    global unsafeCases
    content = page.GetContent()
    currentLocation = page.Title
    extraNote = ""
    for template in page.GetTemplates(): #Will only fix the first template occurance, and not any more
        if archiveTemplates.search(template.Template):
            if "archive" in template.Args and not "key" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location, as well as cleaning up any issues left behind
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    verbose("Archive Fix", f"{page} currently has {archiveLocation}, but we should have something with {currentLocation}")
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(?:/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee] %\(counter\)d)").search(archiveLocation) #For simplicity, only deal with %(counter)d
                    if existingArchive:
                        wantedLocation = existingArchive.group()
                        verbose("Archive Fix", f"Attempting to preserve {wantedLocation}")
                        if wantedLocation[0] == "/": #Stupid but eh
                            newArchive = currentLocation+wantedLocation
                        else:
                            newArchive = currentLocation+"/"+wantedLocation

                        #Verify this archive is valid by checking if it exists
                        archivePage = Article(newArchive.replace(r"%(counter)d", "1"))
                        if not archivePage.exists or archivePage.IsRedirect:
                            #At this point, we attempt to move pages from the old name, in case the mover just happened to forget
                            lwarn(f"[FixArchiveLocation] {currentLocation} failed safety check (Missing expected archives), checking previous pages")
                            wasFixed = DetermineBadMove(page)
                            if wasFixed: #Final confirmation that the fix worked
                                archivePage = Article(newArchive.replace(r"%(counter)d", "1"))
                                if archivePage.exists and not archivePage.IsRedirect:
                                    lsucc("[FixArchiveLocation] Fixing archive location now that subpages have been moved")
                                    template.ChangeKeyData("archive", newArchive)
                                    content = content.replace(template.Original, template.Text)
                                    if wasFixed > 1:
                                        extraNote = f"; {wasFixed} subpages moved"
                                    elif wasFixed == 1:
                                        extraNote = f"; {wasFixed} subpage moved"
                                else:
                                    lalert("[FixArchiveLocation] We moved some subpages yet it seems broken still?")
                                    unsafeCases[currentLocation] = "Subpages moved, but can't confirm fix"
                            break

                        else: #Archive exists just fine
                            verbose("Archive Fix", "Safety test has been passed")
                            template.ChangeKeyData("archive", newArchive)
                            content = content.replace(template.Original, template.Text)
                            break
                    else: #Regex did not match
                        lalert(f"[FixArchiveLocation] Couldn't find recognised archive for {page}")
                        unsafeCases[currentLocation] = "Couldn't find a recognised archive value"
                        break
                else: #Value passed the test and shouldn't be categorised
                    lwarn(f"[FixArchiveLocation] {page} does not seem to be malformed")
                    unsafeCases[currentLocation] = "No issues found but it's in the category"
                    break
            elif not "archive" in template.Args: #No archive key
                lwarn(f"[FixArchiveLocation] {page}'s template doesn't have an archive key")
                unsafeCases[currentLocation] = "No archive key present"
    if content != page.GetContent():
        page.edit(content, f"Fixed archive location for Lowercase Sigmabot III{extraNote} ([[User:MiszaBot/config#Parameters explained|More info]] - [[User talk:{username}|Report bot issues]])", minorEdit=True)

# CheckArchiveLocations(Article(f"User:{username}/encoded–title"))
prevHour = datetime.datetime.now().hour-1 #Hourly checks
while True:
    curHour = datetime.datetime.now().hour
    if curHour != prevHour:
        prevHour = curHour
        log("[FixArchiveLocation] Beginning cycle")
        IterateCategory("Category:Pages where archive parameter is not a subpage", CheckArchiveLocations)
        log("[FixArchiveLocation] Finished cycle")
        if len(unsafeCases) == 0:
            Article(f"User:{username}/helpme/Task2").edit("No problems", "[Task 2] No problems")
        else:
            problematicList = ""
            for page, reason in unsafeCases.items():
                problematicList += f"\n* [[:{page}]] - {reason}"
            Article(f"User:{username}/helpme/Task2").edit(f"Encountered some issues with archives on the following pages:{problematicList}", f"[Task 2] Requesting help on {len(unsafeCases)} page(s)")
        unsafeCases.clear()
    else:
        time.sleep(1)