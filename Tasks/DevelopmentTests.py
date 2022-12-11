#Demonstration and testing stuff

# basename = "J'Adore Parfum d'Eau"

# page = Article(f"Talk:{basename}")
# print("Got page",page)
# print("Linked, Linked.Linked =",page.GetLinkedPage(),page.GetLinkedPage().GetLinkedPage())

# print(page.GetSubpages())

dummy = f"User:{username}/dummy%27%22%26%3Fpage"
title = fr"User:{username}/title%27%22%26%3Ftest2"

def MainTester(page):
    article = Article(page)
    print(page,article,article.exists())
    print(article.GetSubpages())

    if page == title:
        print("title!")
        for h in article.GetHistory():
            a,b,c = h.IsMove()
            if a:
                print(b,c)
                d,e = Article(b), Article(c)
                print(d,d.exists(), "  |  ", e, e.exists())
    elif page == dummy:
        print("dummy!")
        # article.edit("SA test for making sure processes work under new system","Edit test")

print("GOING") #testing
IterateCategory("Category:Pages where archive parameter is not a subpage",MainTester)
print("AND HES GONE")