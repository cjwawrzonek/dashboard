import logging
import re


# TODO move this elsewhere
def _stringToIntIfPossible(s):
    # if (typeof s == "object" && "map" in s) {
    #     return s.map(_stringToIntIfPossible);
    # } else {
    if isinstance(s, str) or isinstance(s, unicode):
        if re.match('^[0-9]+$', s) is not None:
            return int(s)
    return s


# TODO move this elsewhere
# go through and collapse any single-element arrays (but not nested
# arrays)
def collapseSingleArrays(doc):
    for i in doc:
        if isinstance(doc[i], list):
            # array
            if len(doc[i]) == 1:
                doc[i] = doc[i][0]
        elif isinstance(doc[i], dict):
            # document, recurse
            doc[i] = collapseSingleArrays(doc[i])
        else:
            # some native type, no recurse
            pass
    return doc


class Mdiag:
    """ An mdiag document in euphonia.mdiags. It is a JSON product of the
    mdiag.sh script. """
    def __init__(self, doc):
        self.doc = doc
        self.logger = logging.getLogger('logger')

    def getError(self):
        # self.logger.debug("getError()")
        return self.doc.get('error')

    def getHost(self):
        # self.logger.debug("getHost()")
        return self.doc.get('host')

    def getOutput(self):
        # self.logger.debug("getOutput()")
        return self.doc.get('output')

    def getRef(self):
        # self.logger.debug("getRef()")
        return self.doc.get('ref')

    def getRun(self):
        # self.logger.debug("getRun()")
        return self.doc.get('run')

    def getSection(self):
        # self.logger.debug("getSection()")
        return self.doc.get('section')

    def getSubsection(self):
        # self.logger.debug("getSubsection()")
        return self.doc.get('subsection')

    def getTimestamp(self):
        # self.logger.debug("getTimestamp()")
        return self.doc.get('ts')

    def getVersion(self):
        # self.logger.debug("getVersion()")
        return self.doc.get('version')

    def getSysfsSelection(self):
        # self.logger.debug("getSysfsSelection()")
        if 'filename' in self.doc and self.doc['filename'].startswith("/sys/") and\
                'exists' in self.doc and self.doc['exists'] is True and\
                'content' in self.doc and len(self.doc['content']) == 1 and\
                self.doc['content'][0].find(" ") >= 0 and\
                self.doc['content'][0].find("[") >= 0:
            words = self.doc['content'][0].split(" ")
            for word in words:
                if word == "":
                    continue
                if word.startswith("[") and word.endswith("]"):
                    word = word[1:-1]
                    return word
        return None

    def getSysctl(self):
        # self.logger.debug("getSysctl()")
        if 'section' in self.doc and self.doc['section'] == "sysctl" and\
                'output' in self.doc and len(self.doc['output']) > 0:
            values = {}
            for line in self.doc['output']:
                words = line.split(" = ")
                if len(words) > 2:
                    value = words.slice(1).join(" = ")
                else:
                    value = words[1]
                if value.find("\t") >= 0:
                    value = value.split("\t")
                value = _stringToIntIfPossible(value)

                thing = values
                bits = words[0].split(".")
                lastbit = bits.pop()
                for bit in bits:
                    if bit not in thing:
                        thing[bit] = {}
                    thing = thing[bit]
                if lastbit in thing:
                    thing[lastbit].append(value)
                else:
                    thing[lastbit] = [value]

        return collapseSingleArrays(values)

    def getNumaNodes(self):
        nodes = {}
        if 'filename' in self.doc and\
                self.doc['filename'] == "/proc/zoneinfo" and\
                'exists' in self.doc and self.doc['exists'] is True and\
                'content' in self.doc:
            for line in self.doc['content']:
                m = re.match('^Node ([0-9]+), zone +([^\W]+)$', line)
                if m is not None:
                    node_num = int(m.group(1))
                    if node_num not in nodes:
                        nodes[node_num] = []
                    nodes[node_num].append(m.group(2))
        return nodes

    def getProcessName(self):
        if self.getOutput() is not None and len(self.getOutput()) >= 1:
            m = re.match("(^|/)(mongo(d|s||stat|top|import|export|dump|restore|perf|mongodb-mms-(monitoring|backup|automation)-agent))(\.exe)?$", self.getOutput()[0])
            if m is not None:
                return m.group(2)
        return None

    def getProcessPid(self):
        if self.getSection() is not None:
            m = re.match('^proc/([0-9]+)$', self.getSection())
            if m is not None:
                return m.group(1)
        return None
