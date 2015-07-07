def getSubdocs(doc, projection):
    # get the subdocuments based on the projection
    # similar to how projection works in the find command
    # NOTE plural because we expand arrays
    res = []
    subdoc = doc
    subdocTree = projection.split(".")
    # iterate through the subdocuments
    for i in range(len(subdocTree)):
        key = subdocTree[i]
        # if subdoc is an array, we must loop over it
        # for the rest of the projection
        if isinstance(subdoc, list):
            for item in subdoc:
                res.extend(getSubdocs(item, '.'.join(subdocTree[i:])))
            return res
        elif subdoc is None:
            pass
        else:
            if key in subdoc:
                subdoc = subdoc[key]
            else:
                subdoc = None
                break
    res.append(subdoc)
    return res

def getObjectId(id):
    """ Return an ObjectId for the given id """
    if not isinstance(id, bson.ObjectId):
        try:
            id = bson.ObjectId(id)
        except Exception as e:
            return e
    return id

def loadJson(self, string):
    """ Return a JSON-validated dict for the string """
    self.logger.debug("loadJson(%s)", string)
    try:
        res = bson.json_util.loads(string)
    except Exception as e:
        self.logger.exception(e)
        return {'ok': False, 'payload': e}
    return {'ok': True, 'payload': res}