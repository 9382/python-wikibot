#This task will go through all pages in Category:CS1_errors:_format_without_URL and fix clear-cut cases of the improper use of format

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
    namespace = GetNamespace(page)
    if namespace != "Article":
        print("Skipping page not in article namespace",page)
        return
    try:
        raw = GetRawWikiText(page)
    except:
        print("Couldnt get raw of",page)
        return
    # print("Processing",page)
    lastpage = page
    try:
        CiteReferences = GetReferences(raw)
        anychanges = False
        for ref in CiteReferences: #Its a citation error, so look in citations
            refinfo = GetReferenceParameters(ref)
            if "format" in refinfo and not "url" in refinfo: #Cause of the error
                blacklisted = False
                for reg in BlacklistedCases:
                    if regex.compile(reg).search(refinfo["format"].lower()):
                        blacklisted = True #Dont attempt any fixes in this ref
                if not blacklisted:
                    for reg in FixCases:
                        if regex.compile(reg).search(refinfo["format"].lower()):
                            #This is really shady but it works surprisingly well in testing
                            PrecisePosition = FormatLocator.search(ref).span()
                            formatPos = ref.find("format",PrecisePosition[0],PrecisePosition[1])
                            fix = SubstituteIntoString(ref,"type",formatPos,formatPos+6)
                            raw = raw.replace(ref,fix)
                            # print("Found and fixed a case. format=",refinfo["format"],"template=",refinfo["__TEMPLATE"])
                            anychanges = True
        if anychanges:
            ChangeWikiPage(page,raw,f"Changing |format= to |type= (CS1 Error: [[Category:CS1 errors: format without URL||format= without |url=]])")
        return True
    except Exception as exc:
        log(f"Failed to process {page} due to the error of {exc}")
IterateCategory(maincat,CheckPageForErrors)
