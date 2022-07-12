#Just appends text to the bot's sandbox page as a demonstration

while True:
	page = Article(f"User:{username}/sandbox")
	rc = page.GetRawContent()
	print("Got rc")
	time.sleep(10)
	page.edit(rc+"\nContent","Testing edit conflicts",minorEdit=True)
	print("Test edit done")
	time.sleep(20)
