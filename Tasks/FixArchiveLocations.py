#This task fixes the archive parameter for the {{User:MiszaBot/config}} template
import urllib.parse

def CheckArchiveLocations(page):
    article = Article(page)
    if not article.exists():
        #No idea how this would happen since its from a category, but oh well
        log("[FixArchiveLocation] Warning: "+page+" doesn't exist despite being from a category search")
        return
    content = article.GetRawContent()
    content = regex.sub("\n?\[\[Category:Pages where archive parameter is not a subpage\|?[^\]]*\]\]","",content) #Shouldn't be explicitly added
    currentLocation = urllib.parse.unquote(page.replace("_"," "))
    for template in article.GetTemplates():
        if template.Template == "User:MiszaBot/config":
            if "archive" in template.Args and not "key" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location
                #Note that we should try to figure out the formatting before-hand to keep it consistent
                #Note that this could easily fall flat when presented with GIGO as its a bit of a shot in the dark
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    verbose("Archive Fix",f"{page} currently has {archiveLocation}, but we should have something with {currentLocation}")
                    #Most common case: Result of a page move, no GIGO problems
                    existingArchive = regex.compile("(/|^)([Aa][Rr][Cc][Hh][Ii][Vv][Ee]([Ss]/| |%).+)").search(archiveLocation)
                    if existingArchive:
                        wantedLocation = existingArchive.group()
                        verbose("Archive Fix",f"Attempting to preserve {wantedLocation}")
                        if wantedLocation[0] == "/": #Stupid but eh
                            template.ChangeKeyData("archive",currentLocation+wantedLocation)
                        else:
                            template.ChangeKeyData("archive",currentLocation+"/"+wantedLocation)
                        content = content.replace(template.Original,template.Text)
                        continue
                    #else: cry(). its GIGO time
                    #If the above check fails, vandalism is a likely scenario
                    #While we could code something to check previous revisions or look for naming patterns, we could also leave it to humans
                    #And thats what we shall do
                    log(f"Somehow reached the GIGO step in FixArchiveLocations for {page}. This should be fixed by a human and considered for fix by this script")
                elif content == article.RawContent: #The earlier regex.sub caught nothing and theres no archive fail - this shouldnt happen
                    log(f"[FixArchiveLocation] {page} does not seem to be malformed. Unsure how they ended up here. Trying a null edit...")
                    content = content + "\n"
    if content != article.RawContent:
        article.edit(content,f"Fix archive location for Lowercase Sigmabot III ([[User:MiszaBot/config#Parameters explained|More info]] - [[User talk:{username}|Report bot issues]])")
    return True

# CheckArchiveLocations("User_talk:Aidan9382-Bot/sandbox")
looptime = 600 #10 minutes
curtime = time.time()-looptime
while True:
    if curtime + looptime < time.time():
        log("[FixArchiveLocation] Beginning cycle")
        curtime = curtime + looptime
        IterateCategory("Category:Pages where archive parameter is not a subpage",CheckArchiveLocations)
        log(f"[FixArchiveLocation] Finished cycle in {time.time()-curtime} seconds. Next cycle will occur in {curtime+looptime-time.time()} seconds")
    else:
        time.sleep(1)
