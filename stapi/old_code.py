        @b.route('/issue')
        # @authenticated
        def issue_list(**kwargs):
            # TODO implement no-way, Jose 404
            return fail()

        @b.route('/<collection>/query/<query>/proj/<proj>')
        @b.route('/query')
        # @authenticated
        # def basic_query(collection, query, proj, **kwargs):
        def basic_query(**kwargs):
            #star timer here
            logger.debug("Time to start of basic_query : " + str(time.time() % 10) + "\n")

            col = bottle.request.query.get('col', None)
            query = bottle.request.query.get('query', None)
            proj = bottle.request.query.get('proj', None)

            # self.logger.info("The query : " + str(query))

            """TODO: Return this as an html response with an error"""
            if col is None:
                raise ValueError("Error: 'col' must have a value")

            temp = issue_response(self.get, col=col, query=query, proj=proj, **kwargs)

            logger.debug("Time to after issue_response : " + str(time.time() % 10) + "\n")

            # ret = bson.json_util.dumps(temp)
            # ret = str(temp)

            logger.debug("Time to after bson dumps : " + str(time.time() % 10) + "\n")

            logger.debug("\nEnd\n\n")

            # bottle.response.content_type = 'application/json'

            return temp

""""""

        def issue_response(method, id=None, col=None, query=None, proj=None, **kwargs):
            logger.debug("Time to beginning of issue_resp : " + str(time.time() % 10) + "\n")
            if id is not None:
                res = method(id, **kwargs)
            else:
                res = method(col, query, proj, **kwargs)

            logger.debug("Time to right before success() : " + str(time.time() % 10) + "\n")

            if res['ok']:
                temp = success(res['payload'])

                logger.debug("Time to after success() : " + str(time.time() % 10) + "\n")

                return temp
            return error(res['payload'])

""""""

    """This is the general method for making queries to the database"""
    """ This is not RESTful!!! """
    # Public API function
    # @staticmethod
    def find(self, collection, query=None, proj=None, **kwargs):
        endpoint = '/query'
        # endpoint = '/' + collection + '/query/'

        if query is None:
            pass
            # endpoint += '{}/proj/'
        else:
            """Check if the query was passed as a string or as a dict. If
            it was passed as a dict, convert it to string for url passage"""
            if type(query) is dict:
                query = bson.json_util.dumps(query)
                # query = ''.join(bson.json_util.dumps(query).split())
            elif type(query) is not str:
                # query = bson.json_util.loads(query)
                raise TypeError("Type Error in stapiclient.find(): query is "
                    "of type %s. Expected type <dict> or <str>")
            # Remove whitespace/tabs/newlines from the query and update endpoint
            # endpoint = endpoint + ''.join(query.split()) + '/proj/'

        if proj is None:
            pass
            # endpoint += '{}'
        else:
            """Check if the proj was passed as a string or as a dict. If
            it was passed as a dict, convert it to string for url passage"""
            if type(proj) is dict:
                proj = bson.json_util.dumps(proj)
            elif type(proj) is not str:
                raise TypeError("Type Error in stapiclient.find(): proj is "
                    "of type %s. Expected type <dict> or <str>")
            # Remove whitespace/tabs/newlines from the proj and update endpoint
            # endpoint += ''.join(proj.split())

        # Return the getRequest as an array of documents as passed from the API
        params = {}
        params['col'] = collection
        params['query'] = query
        params['proj'] = proj

        return self._getRequest(endpoint, params=params, **kwargs)#['data']#[collection]