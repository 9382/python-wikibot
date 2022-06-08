commoncases = [r"/Archive %(counter)d", r"/Archives/%(year)d/%(monthname)s", r"/Archives/%(year)d/%(monthname)d"]
def CheckArchiveLocations(page):
    article = Article(page)
    if not article.exists():
        #No idea how this would happen since its from a category, but oh well
        log("[FixArchiveLocation] Warning: "+page+" doesn't exist despite being from a category search")
        return
    content = article.GetRawContent()
    content = regex.sub("\n?\[\[Category:Pages where archive parameter is not a subpage\|?[^\]]*\]\]","",content) #Shouldn't be explicitly added
    currentLocation = page.replace("_"," ")
    for template in article.GetTemplates():
        if template.Template == "User:MiszaBot/config":
            if "archive" in template.Args:
                archiveLocation = template.Args["archive"]
                #Attempt to fix the archive location
                #Note that we should try to figure out the formatting before-hand to keep it consistent
                #Note that this could easily fall flat when presented with GIGO as its a bit of a shot in the dark
                if not archiveLocation.startswith(currentLocation+"/"): #Not a subpage
                    #Most common case: Result of a page move, no GIGO problems
                    easyFix = False
                    for commoncase in commoncases:
                        if archiveLocation.find(commoncase) > -1:
                            template.ChangeKeyData("archive",currentLocation+commoncase)
                            content = content.replace(template.Original,template.Text)
                            easyFix = True
                            break
                    if easyFix:
                        continue
                    #else: cry(). its GIGO time
                    #Now we try to find any form of archive location at the end - maybe they use a custom format
                    #A potential call to the move or edit history and some quick checks may help rare cases, but may also be excessive.
                    splitSections = archiveLocation.split("/")
                    latestOccurance = -1
                    index = 0
                    for section in splitSections:
                        if section.lower().find("archive") > -1: #Presumably, the archives start here
                            latestOccurance = index #Find the last one. Who knows, maybe the base page name has archive
                        index += 1
                    if latestOccurance == -1: #No archive subpage format found, defaulting to Archive %(counter)d
                        template.ChangeKeyData("archive",currentLocation+r"/Archive %(counter)d")
                    elif latestOccurance == 0: #Rare and annoying edge case
                        if currentLocation.lower().find("archive") > -1: #No archive present - just the page title
                            template.ChangeKeyData("archive",currentLocation+r"/Archive %(counter)d")
                        else: #Probably forgot page title
                            template.ChangeKeyData("archive",currentLocation+"/".join(splitSections[latestOccurance:]))
                    else: #Normal case
                        template.ChangeKeyData("archive",currentLocation+"/"+"/".join(splitSections[latestOccurance:]))
                    content = content.replace(template.Original,template.Text)
                elif content == article.RawContent: #The earlier regex.sub caught nothing and theres no archive fail - this shouldnt happen
                    log("[FixArchiveLocation] "+page+" does not seem to be malformed. Unsure how they ended up here. Trying a null edit...")
                    content = content + "\n"
    if content != article.RawContent:
        article.edit(content,"Fix archive location for Lowercase Sigmabot III ([[User:MiszaBot/config#Parameters explained|More info]])")
    return True

# CheckArchiveLocations("User_talk:Aidan9382-Bot/sandbox")
looptime = 600 #10 minutes
curtime = time.time()-looptime
while True:
    if curtime + looptime < time.time():
        log("[FixArchiveLocation] Beginning cycle")
        curtime = time.time()
        IterateCategory("Category:Pages where archive parameter is not a subpage",CheckArchiveLocations)
        log(f"[FixArchiveLocation] Finished cycle in {time.time()-curtime} seconds. Next cycle will occur in {curtime+looptime-time.time()} seconds")
    else:
        time.sleep(5)
