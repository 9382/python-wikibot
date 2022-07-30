#This task fixes the archive parameter for the {{User:MiszaBot/config}} template
import urllib.parse

unsafeCases = []
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
        if template.Template == "User:MiszaBot/config" or template.Template == "User:Lowercase sigmabot III/config":
            if "archive" in template.Args and not "key" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location
                #Note that we should try to figure out the formatting before-hand to keep it consistent
                #Note that this could easily fall flat when presented with GIGO as its a bit of a shot in the dark
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    verbose("Archive Fix",f"{page} currently has {archiveLocation}, but we should have something with {currentLocation}")
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee].+)").search(archiveLocation)
                    if existingArchive:
                        wantedLocation = existingArchive.group()
                        verbose("Archive Fix",f"Attempting to preserve {wantedLocation}")
                        if wantedLocation[0] == "/": #Stupid but eh
                            newArchive = currentLocation+wantedLocation
                        else:
                            newArchive = currentLocation+"/"+wantedLocation
                        #Verify this archive is valid by either checking if it exists or if the page has no current subpages
                        #Currently only supports %(counter)d substitution, as year and month would require much more advanced checks
                        if not Article(newArchive.replace(r"%(counter)d","1")).exists():
                            if "counter" in template.Args:
                                if Article(newArchive.replace(r"%(counter)d",template.Args["counter"])).exists():
                                    verbose("Archive Fix","Safety tests have passed")
                                    template.ChangeKeyData("archive",newArchive)
                                    content = content.replace(template.Original,template.Text)
                                    continue
                            #Archive doesnt exist. Now checking for any existing subpages
                            verbose("Archive Fix",f"{currentLocation} failed 1 of 2 safety checks (Missing expected archives)")
                            if len(article.GetSubpages()) > 0:
                                #Too risky to do automatically - could be a case of vandalism or major human error. Should be checked properly
                                log(f"[Archive Fix] {currentLocation} failed 2 of 2 safety checks (Already existing subpages). This is a potential case of GIGO and should be addressed by a human")
                                unsafeCases.append(currentLocation)
                                continue
                        verbose("Archive Fix","Safety tests have passed")
                        template.ChangeKeyData("archive",newArchive)
                        content = content.replace(template.Original,template.Text)
                        continue
                    #else: cry(). its GIGO time
                    #If the above check fails, vandalism is a likely scenario
                    #While we could code something to check previous revisions or look for naming patterns, we could also leave it to humans
                    #And thats what we shall do
                    log(f"Somehow reached the GIGO step in FixArchiveLocations for {page}. This should be fixed by a human and considered for fix by this script")
                    unsafeCases.append(currentLocation)
                elif content == article.RawContent: #The earlier regex.sub caught nothing and theres no archive fail - this shouldnt happen
                    log(f"[FixArchiveLocation] {page} does not seem to be malformed. Unsure how they ended up here. Trying a null edit...")
                    content = content + "\n"
    if content != article.RawContent:
        article.edit(content,f"Fix archive location for Lowercase Sigmabot III ([[User:MiszaBot/config#Parameters explained|More info]] - [[User talk:{username}|Report bot issues]])",minorEdit=True)
    return True

# CheckArchiveLocations(f"User_talk:{username}/sandbox")
looptime = 3600 #1 hour
curtime = time.time()-looptime
while True:
    if curtime + looptime < time.time():
        log("[FixArchiveLocation] Beginning cycle")
        curtime = curtime + looptime
        IterateCategory("Category:Pages where archive parameter is not a subpage",CheckArchiveLocations)
        log(f"[FixArchiveLocation] Finished cycle in {time.time()-curtime} seconds. Next cycle will occur in {curtime+looptime-time.time()} seconds")
        if len(unsafeCases) == 0:
            Article(f"User:{username}/helpme/Task2").edit("No problematic archives\n","[Task 2] No problematic archives")
        else:
            problematicList = "\n".join([f"* [[:{page}]]" for page in unsafeCases])
            Article(f"User:{username}/helpme/Task2").edit(f"Found problematic archives (This is likely the result of vandalism or odd/broken formatting)\n{problematicList}\n",f"[Task 2] Requesting help on {len(unsafeCases)} archive(s)")
        unsafeCases.clear()
    else:
        time.sleep(1)
