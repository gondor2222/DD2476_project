import http.client as hc
import http.client, urllib.parse, json
import re

headers = {"Content-type": "application/json"}

server = "127.0.0.1:9200"
searcharticleurl = "/articles/_search?"
searchuserurl = "/users/_search?"
posturl = "localhost/articles/_doc"
NUM_QUERY_HISTORY = 10
NUM_CLICK_HISTORY = 50
NUM_ARTICLES = 20


def searchArticles(query):
    # Args:
    # query: query to search for
    # Returns:
    # A list of tuples (id, title, categories) for top NUM_ARTICLES results
    #
    conn = hc.HTTPConnection(server)
    conn.request("GET", searcharticleurl + "q=text:" + urllib.parse.quote(query) + "&_source=title,id,text,categories&size=" + (str)(NUM_ARTICLES))
    response = conn.getresponse()
    data = json.loads(response.read())
    conn.close()
    hits = data["hits"]["hits"]
    out = {}
    total = 0
    for hit in hits:
        total = total + hit["_score"]
    for hit in hits:
        text = hit["_source"]["text"].replace("\\n", "\n").replace("\\t","\t").replace("&lt;","<").replace("&gt;",">").replace("&amp;times;","×").replace("&quot;", "\"")
        text = re.sub(r"\[\[([a-zA-Z0-9 -:\.\(\)]*)\]\]", r"\1", text)
        text = re.sub(r"\[\[([a-zA-Z0-9 -:\.\(\)]*)\|([a-zA-Z0-9 -:\.\(\)]*)\]\]", r"\2", text)
        text = re.sub(r"\[\[File:[^\]]*\]\]", r"", text)
        out[hit["_source"]["id"]] = {"title": hit["_source"]["title"],
                                     "text": text,
                                     "categories": hit["_source"]["categories"],
                                     "score": hit["_score"] / total}
    return out, hits


def getArticle(id):
    # Args:
    # id: integer id of article
    # Returns:
    # string, string : article title and article text, if the id exists in the database. else, two empty strings
    conn = hc.HTTPConnection(server)
    conn.request("GET", searcharticleurl + "q=id:" + (str)(id) + "&_source=title,text")
    response = conn.getresponse()
    data = json.loads(response.read())
    conn.close()
    if (data["hits"]["total"] != 1):
        print("Error: article with id %d exists %s times" % (id, data["hits"]["total"]))
        return "", ""
    result = data["hits"]["hits"][0]["_source"]
    return result["title"], result["text"]


def updateUserPreferences(id, categories):
    # Args:
    # id : user id
    # categories: list of strings
    # Returns:
    # 1 if successful, 0 otherwise
    # For every string in the list of categories, the corresponding user category bin is incremented by one.
    conn = hc.HTTPConnection(server)
    conn.request("GET", searchuserurl + "q=id:" + (str)(id) + "&_source=preferences")
    response = conn.getresponse()
    data = json.loads(response.read())
    print(data)
    if (data["hits"]["total"] != 1):
        print("Error: user with id %d exists %d times" % (id, data["hits"]["total"]))
        conn.close()
        return 0
    user = data["hits"]["hits"][0]["_source"]
    preferences = user["preferences"]
    print(preferences)
    for category in categories:
        # print category
        if (category in preferences):
            preferences[category] = preferences[category] + 1
        else:
            preferences[category] = 1
    print(preferences)
    url = ("/users/user/%d/_update" % (id))
    newdata = {
        "doc": {
            "preferences": preferences
        }
    }
    params = json.dumps(newdata)
    conn.request("POST", url, params, {"Content-type": "application/json"})
    response = json.loads(conn.getresponse().read())
    conn.close()
    if (response["result"] == "updated"):
        return 1
    else:
        return 0


def getUserPreference(id, category):
    # Args:
    # id : int
    # category: string
    # Returns:
    # number of hits for this category divided by total number of hits for all categories
    conn = hc.HTTPConnection(server)
    conn.request("GET", searchuserurl + "q=id:" + (str)(id) + "&_source=preferences")
    response = conn.getresponse()
    data = json.loads(response.read())
    conn.close()
    if (data["hits"]["total"] != 1):
        print("Error: user with id %d exists %d times" % (id, data["hits"]["total"]))
        return 0
    user = data["hits"]["hits"][0]["_source"]
    preferences = user["preferences"]
    if not category in preferences:
        return 0
    total = 0
    for cat in preferences:
        total = total + preferences[cat]
    return preferences[category] * 1.0 / total


def getUserPreferences(id):
    # Args:
    # category: string
    # Returns:
    # a list of number of hits for categories divided by total number of hits for all categories
    conn = hc.HTTPConnection(server)
    conn.request("GET", searchuserurl + "q=id:" + (str)(id) + "&_source=preferences")
    response = conn.getresponse()
    data = json.loads(response.read())
    conn.close()
    if (data["hits"]["total"] != 1):
        print("Error: user with id %d exists %d times" % (id, data["hits"]["total"]))
        return 0
    user = data["hits"]["hits"][0]["_source"]
    preferences = user["preferences"]
    total = 0
    out = {}
    for cat in preferences:
        total = total + preferences[cat]
    for cat in preferences:
        # out.append((cat, preferences[cat] * 1.0 / total))
        out[cat] = preferences[cat] * 1.0 / total
    #print("preferences is \n" + str(preferences))
    #print("out is \n" + str(out))
    return out


def addQueryHistory(userID, query, docid=""):
    # Args:
    # id: User ID
    # query: User query
    # Returns: 1 if successful, 0 if not
    # Adds this query to this user's search history in the user database, replacing the oldest query if there are already NUM_QUERY_HISTORY in the history.
    # Args:
    # id : user id
    # categories: list of strings
    # Returns:
    # void
    # For every string in the list of categories, the corresponding user category bin is incremented by one.
    conn = hc.HTTPConnection(server)
    conn.request("GET", searchuserurl + "q=id:" + (str)(userID) + "&_source=search_history")
    response = conn.getresponse()
    data = json.loads(response.read())
    if (data["hits"]["total"] != 1):
        print("Error: user with id %d exists %d times" % (userID, data["hits"]["total"]))
        conn.close()
        return 0
    user = data["hits"]["hits"][0]["_source"]
    # print(user)

    history = user["search_history"]
    print((str)(history) + " in addQueryHistory()")
    if query in history:
        clickthrough = history[query]
        if docid != "":
            if len(clickthrough) == NUM_CLICK_HISTORY:
                for i in range(0, NUM_CLICK_HISTORY - 1):
                    clickthrough[i] = clickthrough[i + 1]
                del (clickthrough[-1])
            clickthrough.append(docid)
    else:
        history[query] = []

    print((str)(history) + " in addQueryHistory() after added")
    # history = list(history.items())     # turn the dictionary to list
    # index = len(history)
    # if len(history) == NUM_QUERY_HISTORY:
    #     for i in range(0, NUM_QUERY_HISTORY - 1):
    #         history[i] = history[i + 1]
    #     del (history[-1])
    # history.append(query)
    # history = dict(history)             # turn the list to dictionary
    # print(history)
    url = ("/users/user/%d/_update" % (userID))
    newdata = {
        "doc": {
            "search_history": history
        }
    }

    params = json.dumps(newdata)
    conn.request("POST", url, params, {"Content-type": "application/json"})
    response = json.loads(conn.getresponse().read())
    conn.close()
    if (response["result"] == "updated" or response["result"] == "noop"):
        return 1
    else:
        print(response)
        return 0

def getUserHistory(userID):
    conn = hc.HTTPConnection(server)
    conn.request("GET", searchuserurl + "q=id:" + (str)(userID) + "&_source=search_history")
    response = conn.getresponse()
    data = json.loads(response.read())
    print(data)
    if (data["hits"]["total"] != 1):
        print("Error: user with id %d exists %d times" % (userID, data["hits"]["total"]))
        conn.close()
        return 0
    user = data["hits"]["hits"][0]["_source"]
    conn.close()
    print((str)(user['search_history']) + " in getUserHistory()")
    return user['search_history']

def getTermVectors(docId):
    '''
    param: docId
    return: dictionary with terms as keys and values are a dictionary of the form:
    {
        "term_freq": tf,
        "tokens": [{
            "position": 80,
            "start_offset": 538,
            "end_offset": 539
        },...]
    }
    '''
    conn = hc.HTTPConnection(server)
    new_data = {
        "fields":["text"]
    }
    params = json.dumps(new_data)
    conn.request("POST", '/articles/article/'+docId+'/_termvectors', params, \
                 {"Content-type": "application/json"})
    response = conn.getresponse()
    data = json.loads(response.read())
    terms = data['term_vectors']['text']['terms']
    conn.close()
    return terms


def main():
    title, text = getArticle(3333)
    # print title
    # print text
    # updateUserPreferences(5, ["sports", "testcategory"])
    # print(getUserPreference(5, "testcategory"))
    # addQueryHistory(5, "q13")
    list = searchArticles("Alan Turing")
    # for article in list:
    #    print article[0] + " " + article[1]
    #    for category in article[2]:
    #        print category, "****",
    #    print
    #    print
    preferences = getUserPreferences(5)
    # print("Haha: %d" % (preferences))
    for entry in preferences:
        print(entry[0] + " " + str(entry[1]))


if __name__ == "__main__":
    main()



