#This task fixes the archive parameter for the {{User:MiszaBot/config}} template as well as other small factors

unsafeCases = {}
archiveTemplates = regex.compile("[Uu]ser:([Mm]iszaBot|[Ll]owercase sigmabot III)/config")
def DetermineBadMove(article):
    global unsafeCases
    #Attempts to determine if pages from before weren't moved under the new name
    currentLocation = urllib.parse.unquote(article.StrippedArticle.replace("_"," "))
    pagehistory = article.GetHistory(8)
    for revision in pagehistory:
        wasMoved,From,To = revision.IsMove()
        if wasMoved:
            verbose("Archive Fix",f"Examining the move from {revision.DateText} by {revision.User}")
            if (datetime.datetime.now() - revision.Date).total_seconds() < 60*60*6:
                log("[FixArchiveLocation] Move was too recent, avoiding fixing it just yet")
                #unsafeCases[currentLocation] = "Move was too recent, not fixing it yet..." #Dont alert help page just yet
            else:
                prevPage = Article(From)
                if not prevPage.exists():
                    lalert("Archive Fix","Previous page doesn't exist, that isn't right")
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
                    if not subpage.StrippedArticle.startswith(prevPage.StrippedArticle+"/Archive"):
                        #If the page is not an archive, to avoid the "A/B/Subpage listed under A" situation, ensure the page doesnt have a non-talk version
                        if subpage.GetLinkedPage().exists():
                            unsafeCases[currentLocation] = "Some subpages didn't meet the automove criteria"
                            return
                #All cool, go ahead and move
                for subpage in articleSubpages:
                    subpage.MoveTo(
                        currentLocation+subpage.StrippedArticle[len(prevPage.StrippedArticle):],
                        "Re-locating talkpage archive under new page title"
                    ) #Move to new page with subpage suffix kept
                return True
            return #Only checks the most recent move, and no further
    unsafeCases[currentLocation] = "No recent enough page moves found"

def CheckArchiveLocations(page):
    global unsafeCases
    article = Article(page)
    if not article.exists():
        #No idea how this would happen since its from a category, but oh well
        lwarn(f"[FixArchiveLocation] Warning: {page} doesn't exist despite being from a category search")
        return
    content = article.GetRawContent()
    currentLocation = urllib.parse.unquote(page.replace("_"," "))
    for template in article.GetTemplates(): #Will only fix the first template occurance, and not any more
        if archiveTemplates.search(template.Template):
            if "archive" in template.Args and not "key" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location, as well as cleaning up any issues left behind
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    verbose("Archive Fix",f"{page} currently has {archiveLocation}, but we should have something with {currentLocation}")
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(?:/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee] %\(counter\)d)").search(archiveLocation) #For simplicity, only deal with %(counter)d
                    if existingArchive:
                        wantedLocation = existingArchive.group()
                        verbose("Archive Fix",f"Attempting to preserve {wantedLocation}")
                        if wantedLocation[0] == "/": #Stupid but eh
                            newArchive = currentLocation+wantedLocation
                        else:
                            newArchive = currentLocation+"/"+wantedLocation

                        #Verify this archive is valid by checking if it exists
                        archivePage = Article(newArchive.replace(r"%(counter)d","1"))
                        if not archivePage.exists() or archivePage.IsRedirect():
                            #Too risky to do automatically - could be a case of vandalism or human error. Should be checked manually
                            lwarn(f"[FixArchiveLocation] {currentLocation} failed safety check (Missing expected archives), checking previous pages")
                            wasFixed = DetermineBadMove(article)
                            if wasFixed:
                                archivePage = Article(newArchive.replace(r"%(counter)d","1"))
                                if archivePage.exists() and not archivePage.IsRedirect():
                                    lsucc("[FixArchiveLocation] Fixing archive location now that subpages have been moved")
                                    template.ChangeKeyData("archive",newArchive)
                                    content = content.replace(template.Original,template.Text)
                                else:
                                    lwarn("[FixArchiveLocation] We moved some subpages yet it seems broken still?")
                                    unsafeCases[currentLocation] = "Subpages moved, but can't confirm fix"
                            break
                        else:
                            verbose("Archive Fix","Safety test has been passed")
                            template.ChangeKeyData("archive",newArchive)
                            content = content.replace(template.Original,template.Text)
                            break
                    else:
                        lalert(f"[FixArchiveLocation] Couldn't find recognised archive for {page}")
                        unsafeCases[currentLocation] = "Couldn't find a recognised archive parameter"
                        break
                else:
                    lwarn(f"[FixArchiveLocation] {page} does not seem to be malformed")
                    unsafeCases[currentLocation] = "No issues found but it's in the category"
                    break

    if content != article.RawContent:
        article.edit(content,f"Fix archive location for Lowercase Sigmabot III ([[User:MiszaBot/config#Parameters explained|More info]] - [[User talk:{username}|Report bot issues]])",minorEdit=True)
    return True

# CheckArchiveLocations(f"User talk:{username}/sandbox")
looptime = 3600 #1 hour
curtime = time.time()-looptime
while True:
    if curtime + looptime < time.time():
        log("[FixArchiveLocation] Beginning cycle")
        curtime = curtime + looptime
        IterateCategory("Category:Pages where archive parameter is not a subpage",CheckArchiveLocations)
        log(f"[FixArchiveLocation] Finished cycle in {time.time()-curtime} seconds. Next cycle will occur in {curtime+looptime-time.time()} seconds")
        if len(unsafeCases) == 0:
            Article(f"User:{username}/helpme/Task2").edit("No problems\n","[Task 2] No problematic archives")
        else:
            problematicList = ""
            for page,reason in unsafeCases.items():
                problematicList += f"\n* [[:{page}]] - {reason}"
            Article(f"User:{username}/helpme/Task2").edit(f"Encountered some issues with archives on the following pages:{problematicList}\n",f"[Task 2] Requesting help on {len(unsafeCases)} archive(s)")
        unsafeCases.clear()
    else:
        time.sleep(1)
