#This task fixes the archive parameter for the {{User:MiszaBot/config}} template

unsafeCases = {}
archiveTemplates = regex.compile("[Uu]ser:([Mm]iszaBot|[Ll]owercase sigmabot III)/config")
def CheckArchiveLocations(page):
    global unsafeCases
    article = Article(page)
    if not article.exists():
        #No idea how this would happen since its from a category, but oh well
        log(f"[FixArchiveLocation] Warning: {page} doesn't exist despite being from a category search")
        return
    content = article.GetRawContent()
    content = regex.sub("\n?\[\[Category:Pages where archive parameter is not a subpage\|?[^\]]*\]\]","",content) #Shouldn't be explicitly added
    currentLocation = urllib.parse.unquote(page.replace("_"," "))
    for template in article.GetTemplates():
        if archiveTemplates.search(template.Template):
            if "archive" in template.Args and not "key" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location
                #Note that we should try to figure out the formatting before-hand to keep it consistent
                #Note that this could easily fall flat when presented with GIGO as its a bit of a shot in the dark
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    verbose("Archive Fix",f"{page} currently has {archiveLocation}, but we should have something with {currentLocation}")
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee] %\(counter\)d)").search(archiveLocation) #For the sake of my sanity, only deal with %(counter)d
                    if existingArchive:
                        wantedLocation = existingArchive.group()
                        verbose("Archive Fix",f"Attempting to preserve {wantedLocation}")
                        if wantedLocation[0] == "/": #Stupid but eh
                            newArchive = currentLocation+wantedLocation
                        else:
                            newArchive = currentLocation+"/"+wantedLocation
                        #Verify this archive is valid by either checking if it exists or if the page has no current subpages
                        #Currently only supports %(counter)d substitution, as year and month would require much more advanced checks
                        archivePage = Article(newArchive.replace(r"%(counter)d","1"))
                        if not archivePage.exists() or archivePage.IsRedirect():
                            #Too risky to do automatically - could be a case of vandalism or major human error. Should be checked manually
                            lalert(f"[Archive Fix] {currentLocation} failed safety checks (Missing expected archives)")
                            unsafeCases[currentLocation] = "Missing expected archives"
                            continue
                        verbose("Archive Fix","Safety tests have passed")
                        template.ChangeKeyData("archive",newArchive)
                        content = content.replace(template.Original,template.Text)
                        continue
                    #else: cry(). its GIGO time
                    #If the above check fails, vandalism is a likely scenario
                    #While we could code something to check previous revisions or look for naming patterns, we could also leave it to humans
                    #And thats what we shall do
                    lalert(f"Couldn't find existing archive for {page}. I'm not gonna try fix this myself")
                    unsafeCases[currentLocation] = "Couldn't find valid archive parameter"
                elif content == article.RawContent: #The earlier regex.sub caught nothing and theres no archive fail - this shouldnt happen
                    log(f"[FixArchiveLocation] {page} does not seem to be malformed. Unsure how they ended up here. Trying a null edit...")
                    content = content + "\n"
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
