#Demonstration and testing stuff

time.sleep(1)
page = Article(f"User:{username}/dummypage")
print("Got page")
page.MoveTo(f"User:{username}/dummypage2","Testing movement")
print("Moved")
