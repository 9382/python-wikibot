#Just appends text to the bot's sandbox page

Template = f"User:{username}/sandbox"
rawtext = GetWikiRawText(Template)
ChangeWikiPage(Template,rawtext+"\nContent","Automated Test edit")
print("Test edit done")