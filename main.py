from dotenv import dotenv_values
from datetime import datetime
import re as regex
import threading
import requests
import random
import time
import os
SUBMITEDITS = False #Set to True when you want the bot to actually change a page's content (AKA not debugging)
EnabledTasks = ["FixImproperUseOfFormat"] #List of tasks set to run. Simply put the filenames from /Tasks/ without the .py

#Do NOT edit below this line unless you understand what any of it means (its quite fragile)

def currentDate():
    #The current date in YYYY-MM-DD hh:mm:ss
    return str(datetime.fromtimestamp(time.time()//1))
def safeWriteToFile(filename,content,mode="w",encoding="UTF-8"):
    #Writes contents to a file, auto-creating the directory should it be missing
    if filename.find("\\") > -1:
        try:
            os.makedirs("/".join(filename.replace("\\","/").split("/")[:-1]),exist_ok=True)
        except:
            return False,f"Couldnt make directory for {filename}"
    try:
        file = open(filename,mode,encoding=encoding,newline="")
    except:
        return False,f"Failed to open {filename}"
    try:
        file.write(content)
    except Exception as exc:
        file.close()
        return False,f"Failed to write content for {filename}"
    file.close()
    return True,f"Successfully wrote to {filename}"
def log(content):
    #Manages the writing to a daily log file for debugging
    print(f"[Log {currentDate()[11:]}]",content)
    success,result = safeWriteToFile(f"Logs/{currentDate()[:10]}.log",f"[{currentDate()[11:]}] {content}\n","a")
    if not success:
        print(f"[Log {currentDate()[11:]}] Failed to write to log file: {result}")
    return success
if SUBMITEDITS:
    log("SUBMITEDITS is set to True. Edits will actually be made")
else:
    log("SUBMITEDITS is set to False. Edits will not be requested, only simulated")
username,password = dotenv_values()["USER"],dotenv_values()["PASS"]
enwiki = "https://en.wikipedia.org/"
maxEditsPerMinute = 10
getwithintagsreg = regex.compile('>[^<]+') #Quality
def GetWithinTags(text):
    return getwithintagsreg.search(text).group()[1:]
InQuotereg = regex.compile('"[^"]*')
def GetInQuote(text):
    return InQuotereg.search(text).group()[1:]
cookies = {}
def request(method,page,**kwargs):
    global cookies
    request = getattr(requests,method)(page,cookies=cookies,**kwargs)
    if "set-cookie" in request.headers:
        setcookies = request.headers["set-cookie"].split(", ")
        for cookie in setcookies:
            actualCookie = cookie.split(";")[0]
            moreInfo = actualCookie.split("=")
            if moreInfo[0].find(" ") > -1:
                continue
            cookies[moreInfo[0]] = "=".join(moreInfo[1:])
            # print("Set cookie",moreInfo[0],"with value","=".join(moreInfo[1:]))
    return request
def GetTokenForType(actiontype):
    return request("get",enwiki+f"w/api.php?action=query&format=json&meta=tokens&type=*").json()["query"]["tokens"][f"{actiontype}token"]
boundary = "-----------PYB"+str(random.randint(1e9,9e9))
print("Using boundary",boundary)
def CreateFormRequest(location,d):
    finaltext = ""
    for arg,data in d.items():
        finaltext += f"""{boundary}\nContent-Disposition: form-data; name="{arg}"\n\n{data}\n"""
    finaltext += f"{boundary}--"
    return request("post",location,data=finaltext.encode("utf-8"),headers={"Content-Type":f"multipart/form-data; boundary={boundary[2:]}"})

def GetReferenceParameters(reference):
    result = {}
    starting,ending = reference.find("{{"),reference.find("}}")
    for param in reference[starting+2:ending].split("|"):
        split = param.split("=")
        if not 1 in split and not "__TEMPLATE" in result:
            result["__TEMPLATE"] = param.strip()
        try:
            result[split[0].strip()] = "=".join(split[1:]).strip()
        except:
            continue #Unnammed parameter (Probably a ||)
    return result
wikilinkreg = regex.compile('<a href="/wiki/[^"]+" title="[^"]+">')
WLSpecificreg = regex.compile('"/wiki/[^"]+')
def GetWikiLinks(text):
    return [WLSpecificreg.search(x).group()[7:] for x in wikilinkreg.findall(text)]
wholepagereg = regex.compile('<div id="bodyContent" class="vector-body">(.*\n)+<div c') #THIS IS STUPID
def GetWikiText(article):
    return wholepagereg.search(requests.get(enwiki+"wiki/"+article).text).group()[42:-6]
def GetWholeWikiText(article):
    return requests.get(enwiki+"wiki/"+article,cookies=cookies).text
#The repeated [^X] is probably bad, but oh well!
rawtextreg = regex.compile('<textarea [^>]+>[^<]+</textarea>')
def GetWikiRawText(article):
    content = requests.get(enwiki+"wiki/"+article+"?action=edit",cookies=cookies).text
    rawtext = rawtextreg.search(content).group()
    return regex.sub("&amp;","&",regex.sub("&lt;","<",GetWithinTags(rawtext))) #&lt; and &amp; autocorrection
RefLocator = regex.compile("<ref[^>]*>{{[^}]+}}</ref>") #Note: Only cares about refs using a {{template}}
def GetReferences(text):
    return RefLocator.findall(text)

namespaces = ["User","Wikipedia","WP","File","MediaWiki","Template","Help","Category","Portal","Draft","TimedText","Module"] #Gadget( definition) is deprecated
pseudoNamespaces = {"CAT":"Category","H":"Help","MOS":"Wikipedia","WP":"Wikipedia","WT":"Wikipedia talk",
                    "Project":"Wikipedia","Project_talk":"Wikipedia talk","Image":"File","Image_talk":"File talk",
                    "WikiProject":"Wikipedia","T":"Template","MP":"Article","P":"Portal","MoS":"Wikipedia"}
def GetNamespace(articlename):
    for namespace in namespaces:
        if articlename.startswith(namespace+":"):
            return namespace
        if articlename.startswith(namespace+"_talk:"):
            return namespace+" talk"
    prefix = articlename.split(":")[0]
    if prefix in pseudoNamespaces:
        return pseudoNamespaces[prefix]
    if articlename.startswith("Talk:"):
        return "Talk"
    if articlename.startswith("Special:"):
        return "Special"
    return "Article"

lastEditTime = 0
editCount = 0
def ChangeWikiPage(article,newcontent,editsummary):
    global lastEditTime
    global editCount
    editCount += 1
    if editCount % 10 == 0:
        print("Edit count:",editCount) #Purely statistical
    if not SUBMITEDITS:
        return print(f"Not submitting changes to {article} as SUBMITEDITS is set to False")
    log(f"Making edits to {article}:\n    {editsummary}")
    global lastEditTime
    EPS = 60/maxEditsPerMinute #Incase you dont wanna go too fast
    if time.time()-lastEditTime < EPS:
        print("Waiting for edit cooldown to wear off")
    while time.time()-lastEditTime < EPS:
        time.sleep(.2)
    lastEditTime = time.time()
    return CreateFormRequest(enwiki+f"/w/index.php?title={article}&action=submit",{"wpUnicodeCheck":"ℳ𝒲♥𝓊𝓃𝒾𝒸ℴ𝒹ℯ","wpTextbox1":newcontent,"wpSummary":editsummary,"wpEditToken":GetTokenForType("csrf"),"wpUltimateParam":"1"})

def SubstituteIntoString(wholestr,substitute,start,end):
    return wholestr[:start]+substitute+wholestr[end:]
log(f"Attempting to log-in as {username}")
CreateFormRequest(enwiki+f"w/api.php?action=login&format=json",{"lgname":username,"lgpassword":password,"lgtoken":GetTokenForType("login")}) #Set-Cookie handles this
if not "centralauth_User" in cookies:
    log(f"[!] Failed to log-in as {username}, check the password and username are correct")
    exit()
log("Successfully logged in")

#Task loader
log("Attempting to load tasks...")
execList = {}
#Odd approach but it works
for file in os.listdir("Tasks"):
    if not file.endswith(".py"):
        continue
    if not os.path.isfile("Tasks/"+file):
        continue
    if file[:-3] in EnabledTasks: #Removes .py extension
        execList[file] = bytes("#coding: utf-8\n","utf-8")+open("Tasks/"+file,"rb").read()
    else:
        log(f"[Tasks] Skipping task {file} as it is not enabled")
for file,contents in execList.items():
    try:
        log(f"[Tasks] Running task {file}")
        taskThread = threading.Thread(target=exec,args=(contents,globals()))
        taskThread.start()
    except Exception as exc:
        log(f"[Tasks] Task {file} loading error -> {exc}")
log("Finished loading tasks")
while True:
    time.sleep(120)
    tasks = threading.active_count()
    log(f"Active task count: {tasks-1}")
    if tasks == 1:
        log("All tasks seem to have been terminated or finished. Exiting script in 15 seconds..")
        time.sleep(15)
        break
