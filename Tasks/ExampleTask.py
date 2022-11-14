#Demonstration and testing stuff

page = Article(f"User talk:{username}/sandbox")
print("Got page, examining history")
for revision in page.GetHistory():
	if revision.IsMinor():
		print("Minor revision on",revision.Date,"-",revision.ID)
	isMove,From,To = revision.IsMove()
	if isMove:
		print("Moving revision from",From,"to",To,"on",revision.Date,"-",revision.ID)
