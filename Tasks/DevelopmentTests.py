#Demonstration and testing stuff

page = Article(f"User talk:{username}/sandbox")
print("Got page",page)
print("Linked, Linked.Linked =",page.GetLinkedPage(),page.GetLinkedPage().GetLinkedPage())

page = Article(f"Talk:East Pakistan Province")
print(page.GetHistory(8))