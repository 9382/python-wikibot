#Demonstration and testing stuff

from wikitools import *

def __main__():
    print("username", username, "userid", userid)

    """ General tests """
    test = Article(f"User:{username}")
    print(test,test.exists,test.Namespace,test.Title)

    test = Article(f"User:{username}/A–+- B'\"&?")
    print(test,test.exists,test.Namespace,test.Title)

    print("GET CONTENT AND EDIT")
    content = test.GetContent()
    print("content=",content)
    # test.edit(content+"\nTest edit","Testing botpass")

    print("GET HISTORY")
    for x in test.GetHistory(6):
        # print(x.Comment)
        print(x.IsMove())

    print("GET SUBPAGES")
    print(test.GetSubpages())

    # print("Move page?")
    # test.MoveTo(f"User:{username}/–+- A '\"&?","Page move test")

    print("WikiConfig test")
    Config = WikiConfig(f"User:{username}/DevelopmentTests/config", {
        "Value1": False,
        "Value2": "Stringg",
        "Value3": 2839
    })
    print("Config round 1", Config.get("Value1"), Config.get("Value2"), Config.get("Value3"), Config.get("Value4"))
    Config.update()
    print("Config round 2", Config.get("Value1"), Config.get("Value2"), Config.get("Value3"), Config.get("Value4"))
    """ """
