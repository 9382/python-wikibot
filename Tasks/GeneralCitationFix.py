#This task will go through all pages in Category:CS1_errors:_format_without_URL and fix clear-cut cases of the improper use of format
#This task is currently withdrawn / denied and doesnt have a hopeful outlook

cbignore = regex.compile("[^ \n]*?{{[Cc]bignore}}")
def GetCitations(article):
    citations = []
    for template in article.GetTemplates():
        if template.Template.lower() == "citation" or template.Template.lower().find("cite ") > -1:
            #Check for {{cbignore}}
            #This is stupid
            templatePosition = article.RawContent.find(template.Text)
            templateEnding = templatePosition+len(template.Text)
            if not cbignore.search(article.GetRawContent()[templateEnding:templateEnding+99]):
                citations.append(template)
    verbose("Citation Fix",f"Found {len(citations)} citation templates from {len(article.GetTemplates())} templates")
    return citations

formatcat = "Category:CS1_errors:_format_without_URL"
FormatLocator = regex.compile("\| *format *= *[^|}]+(\||})")
FixCases = ["(^| )e?-?book","newspaper","magazine","letter","script","(hard|paper)(back|cover)","novel","print","dvd","blu-?ray","disc","obituary"]
BlacklistedCases = ["pdf","doc","audio commentary","digital"] #Audio commentary is a common format in this category. Its not really a "medium", so ill consider it as not wanting to be changed automatically
"""
Edge cases to consider:
  [BL/WL] video (Could be a case of type/medium being more fitting, but also video is an online thing. Most likely not going to include)
  [WL] XYZ pages (Would honestly be better removing the format parameter entirely if this is found, as its unfit)
  [BL] digital (Hard to decide whether or not phrases like "Digitized by GoogleEBook" should be converted or not)
"""
def LookForBadFormat(article):
    #Changes use of format to the more appropriate scenario if relevant
    verbose("Citation Fix","Looking for bad |format=")
    raw = article.GetRawContent()
    for template in GetCitations(article):
        beforehand = template.Text
        if "format" in template.Args and not "url" in template.Args: #Cause of the error
            curformat = template.Args["format"].lower()
            blacklisted = False
            for reg in BlacklistedCases:
                if regex.compile(reg).search(curformat):
                    blacklisted = True #Dont attempt any fixes in this ref
            if not blacklisted:
                for reg in FixCases:
                    if regex.compile(reg).search(curformat):
                        template.ChangeKey("format","type")
                        raw = raw.replace(beforehand,template.Text)
    article.RawContent = raw

badcharcat = "Category:CS1_errors:_invisible_characters"
def LookForBadCharacters(article):
    #Removes characters within citations that arent supported
    verbose("Citation Fix","Looking for invalid characters")
    raw = article.GetRawContent()
    for template in GetCitations(article):
        beforehand = template.Text
        for key,item in list(template.Args.items()):
            for char in item:
                charord = ord(char)
                #See https://en.wikipedia.org/wiki/Category:CS1_errors:_invisible_characters for how this is determined
                if charord == 0x200B: #Zero Width Space
                    item = item.replace(char,"")
                elif charord == 0x200D: #Zero Width Joiner
                    item = item.replace(char,"")
                elif charord == 0x200A: #Hair Space
                    item = item.replace(char,"")
                elif charord == 0xA0: #Non-Breaking Space (Replace instead of remove)
                    item = item.replace(char," ")
                elif charord >= 0 and charord <= 0x1F: #C0 control
                    item = item.replace(char,"")
                elif charord >= 0x80 and charord <= 0x9F: #C1 control
                    item = item.replace(char,"")
            if type(key) == str:
                template.ChangeKeyData(key,item)
        raw = raw.replace(beforehand,template.Text)
    article.RawContent = raw

pipescat = "Category:CS1_errors:_empty_unknown_parameters"
def RemoveExcessivePipes(article):
    #Removes arguments in citations with no content at all
    verbose("Citation Fix","Looking for completely empty parameters")
    raw = article.GetRawContent()
    for template in GetCitations(article):
        beforehand = template.Text
        template.Text = regex.sub("\|[ \n]*(\||}})","\\1",template.Text)
        raw = raw.replace(beforehand,template.Text)
    article.RawContent = raw

isbncat = "Category:CS1_errors:_ISBN"
def CheckISBNs(article):
    #Fixes ISBNs by removing any text before the actual identifier
    verbose("Citation Fix","Looking for bad ISBNs")
    raw = article.GetRawContent()
    for template in GetCitations(article):
        if "isbn" in template.Args:
            beforehand = template.Text
            isbn = template.ChangeKeyData("isbn",regex.sub(".* ([\d\-]{10,})","\\1",template.Args["isbn"]))
            raw = raw.replace(beforehand,template.Text)
    article.RawContent = raw

def CheckPageForErrors(page):
    article = Article(page)
    if not article.Namespace in ["Article","Draft","User"]:
        print("Skipping page not in article namespace",page)
        return
    if not article.exists():
        print("Couldnt get raw of",page)
        return
    try:
        # LookForBadFormat(article) (Disabled due to ambiguity)
        LookForBadCharacters(article)
        RemoveExcessivePipes(article)
        # CheckISBNs(article) (Disabled due to minimal use)
    except Exception as exc:
        log(f"Failed to process {page} due to the error of {exc}")
    else:
        article.edit(article.RawContent,f"Fixed common citation errors ([[User:{username}/citations|More info]] - [[User talk:{username}|Report bot issues]])'")
        return True

looptime = 3600
lastedittime = time.time()-looptime
while True:
    if time.time()-looptime > lastedittime:
        log(f"Starting new cycle of GeneralCitationFix (c-p {time.time()-lastedittime})")
        CheckPageForErrors(f"User:{username}/sandbox")
        # IterateCategory(formatcat,CheckPageForErrors)
        # IterateCategory(badcharcat,CheckPageForErrors)
        # IterateCategory(pipescat,CheckPageForErrors)
        lastedittime = lastedittime + looptime
        log(f"Finished cycle of GeneralCitationFix (c-p {time.time()-lastedittime})")
    else:
        time.sleep(1)