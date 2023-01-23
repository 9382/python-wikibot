#Demonstration and testing stuff

# test = Article(f"User:{username}")
# print(test,test.exists,test.Namespace,test.Title)

# test = Article(f"User:{username}/–+-'\"&?")
# print(test,test.exists,test.Namespace,test.Title)

# print("GET CONTENT AND EDIT")
# content = test.GetContent()
# test.edit(content+"\nTest edit","Testing")

# print("GET HISTORY")
# for x in test.GetHistory(6):
#     # print(x.Comment)
#     print(x.IsMove())

# print("GET SUBPAGES")
# print(test.GetSubpages())

# print("Move page?")
# test.MoveTo(f"User:{username}/–+- A '\"&?","Page move test")

title = f"User:{username}/–+-'\"&?"

def MainTester(page):
    print(page,page.exists)
    print(page.GetSubpages(),page.GetLinkedPage())

    if page.Title == title:
        print("title!")
        print(page)
        print("Content:",page.GetContent())

print("GOING")
IterateCategoryPages("Category:Pages where archive parameter is not a subpage",MainTester)
print("AND HES GONE")