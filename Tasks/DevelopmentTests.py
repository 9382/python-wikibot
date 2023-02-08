#Demonstration and testing stuff

from wikitools import *

""" General tests
test = Article(f"User:{username}")
print(test,test.exists,test.Namespace,test.Title)

test = Article(f"User:{username}/–+-'\"&?")
print(test,test.exists,test.Namespace,test.Title)

print("GET CONTENT AND EDIT")
content = test.GetContent()
test.edit(content+"\nTest edit","Testing")

print("GET HISTORY")
for x in test.GetHistory(6):
    # print(x.Comment)
    print(x.IsMove())

print("GET SUBPAGES")
print(test.GetSubpages())

print("Move page?")
test.MoveTo(f"User:{username}/–+- A '\"&?","Page move test")
"""

def __main__():
    print(username, userid)
    title = f"Talk:Kabir"

    r = Article(title).GetHistory(50)
    print(r)