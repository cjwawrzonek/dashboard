TK421
=====

TK421 is a centralized support hub that runs on top of the support api

To run:
* install the requirements from support services
* make sure the mongod is running with the support data
	* make sure the port matches your .config file
* add the python-lib directory (lives in the directory above this)
  to the PYTHONPATH environment variable
* run `python server.py start --config default.config`
  (or point it at your own config) to start the server.

#### Requirements
* bottle >= 0.12.7
* pymongo >= 2.7.1
* daemon-python >= 2.0.4
