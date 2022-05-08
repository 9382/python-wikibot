#This task will go through all pages in Category:CS1_errors:_format_without_URL and fix clear-cut cases of the improper use of format
#Now inferior to GeneralCitationFix.py

maincat = "Category:CS1_errors:_format_without_URL"
FormatLocator = regex.compile("\| *format *= *[^|}]+(\||})")
FixCases = ["(^| )e?-?book","newspaper","magazine","letter","script","(hard|paper)(back|cover)","novel","print","dvd","blu-?ray","disc","obituary"]
BlacklistedCases = ["pdf","doc","audio commentary","digital"] #Audio commentary is a common format in this category. Its not really a "medium", so ill consider it as not wanting to be changed automatically

"""
Edge cases to consider:
  [BL/WL] video (Could be a case of type/medium being more fitting, but also video is an online thing. Most likely not going to include)
  [WL] XYZ pages (Would honestly be better removing the format parameter entirely if this is found, as its unfit)
  [BL] digital (Hard to decide whether or not phrases like "Digitized by GoogleEBook" should be converted or not)
"""

def CheckPageForErrors(page):
    article = Article(page)
    if not article.Namespace in ["Article","Draft"]:
        print("Skipping page not in article namespace",page)
        return
    if not article.exists():
        print("Couldnt get raw of",page)
        return
    raw = article.GetRawContent()
    try:
        anychanges = False
        for template in article.GetTemplates(): #Its a citation error, so look in citations
            if template.Template.lower() == "citation" or template.Template.lower().find("cite ") > -1:
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
                                raw = raw.replace(template.Original,template.Text)
                                anychanges = True
        if anychanges:
            article.edit(raw,"Changing |format= to |type= (CS1 Error: [[Category:CS1 errors: format without URL||format= without |url=]])")
        return True
    except Exception as exc:
        log(f"Failed to process {page} due to the error of {exc}")
IterateCategory(maincat,CheckPageForErrors)
