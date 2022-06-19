#Just appends text to the bot's sandbox page

while True:
	page = Article(f"User:{username}/sandbox")
	page.edit(page.GetRawContent()+"\nContent","Testing /panic")
	print("Test edit done")
	time.sleep(30)
