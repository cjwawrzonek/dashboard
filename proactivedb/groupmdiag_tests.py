import re
# import datetime
import mdiag

# from collections import defaultdict


class GroupMdiagTests:
    # Note the convention: If it passes the test, then it returns True.
    # Otherwise, it returns false
    @classmethod
    def testTransparentHugepages(cls, groupMdiag):
        # NOTE can also use section transparent_hugepage
        files = ['/sys/kernel/mm/transparent_hugepage/enabled',
                 '/sys/kernel/mm/redhat_transparent_hugepage/enabled']
        # NOTE is this 'exists': True redundant?
        match = {'filename': {"$in": files}, 'exists': True}
        c = groupMdiag.getc(match)
        ids = []
        for doc in c:
            md = mdiag.Mdiag(doc)
            value = md.getSysfsSelection()
            if value == "always":
                ids.append(md.doc['_id'])
        return {'ok': True, 'payload': {'pass': len(ids) == 0, 'ids': ids}}

    @classmethod
    def testNuma(cls, groupMdiag):
        # get the number of numa nodes
        c = groupMdiag.getc({'filename': "/proc/zoneinfo"})
        if c.count() > 0:
            md = mdiag.Mdiag(c.next())
            numaNodes = md.getNumaNodes()
            if numaNodes is not None:
                numNumaNodes = len(numaNodes)
        else:
            return {'ok': False, 'payload': "unable to get /proc/zoneinfo"}

        if numNumaNodes <= 1:
            return {'ok': True, 'payload': {'pass': True, 'ids': []}}

        # there is > 1 numa node
        c = groupMdiag.getc({'section': "sysctl"})
        ids = []
        for doc in c:
            md = mdiag.Mdiag(doc)
            sysctl = md.getSysctl()
            if "vm" in sysctl and "zone_reclaim_mode" in sysctl['vm'] and\
                    sysctl['vm']['zone_reclaim_mode'] != 0:
                ids.append(doc['_id'])
        return {'ok': True, 'payload': {'pass': len(ids) == 0, 'ids': ids}}

    @classmethod
    def testLimits(cls, groupMdiag):
        pidLimits = groupMdiag.getProcPidLimits()

        def checkLimit(limits, name, type, threshold):
            if limits[name][type] < threshold:
                # fail
                return False
            # pass
            return True

        pidIdMap = groupMdiag.getMongoProcesses()
        c = groupMdiag.getc({'_id': {"$in": pidIdMap.values()}})
        ids = []
        for doc in c:
            md = mdiag.Mdiag(doc)
            name = md.getProcessName()
            if name is not None and (name == "mongod" or name == "mongos"):
                pid = md.getProcessPid()
                if pid is not None:
                    limits = pidLimits[pid]
                    if not checkLimit(limits, "nproc", "soft", 32000):
                        ids.append(md.doc['_id'])
                    if not checkLimit(limits, "nproc", "hard", 32000):
                        ids.append(md.doc['_id'])
                    if not checkLimit(limits, "nofile", "soft", 32000):
                        ids.append(md.doc['_id'])
                    if not checkLimit(limits, "nofile", "hard", 32000):
                        ids.append(md.doc['_id'])
        return {'ok': True, 'payload': {'pass': len(ids) == 0, 'ids': ids}}

    @classmethod
    def testKernelMaxPid(cls, groupMdiag):
        # kernel.pid_max = 32768
        section = "sysctl"
        match = "^kernel\\.pid_max\\s*=\\s*(\\d+)"
        conds = { "1": { "$gte": 32768 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testKernelMaxThreads(cls, groupMdiag):
        # kernel.threads-max = 64000
        section = "sysctl"
        match = "^kernel\\.threads-max\\s*=\\s*(\\d+)"
        conds = { "1": { "$gte": 64000 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testKernelMaxOpenFiles(cls, groupMdiag):
        # fs.file-max = 131000
        section = "sysctl"
        match = "^fs\\.file-max\\s*=\\s*(\\d+)"
        conds = { "1": { "$gte": 98000 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def _sectionMatchConditionals(cls, groupMdiag, section, match, conditionals):
        # As the name suggests, for a given section of the mdiag file, a regex
        # match is performed on the output and conditionals are applied to the
        # fields matched in the regex
        ids = []
        query = {'section': section, 'output': {"$exists": 1}}
        c = groupMdiag.getc(query)
        for doc in c:
            md = mdiag.Mdiag(doc)
            output = md.getOutput()
            if output is not None:
                for line in output:
                    m = re.match(match, line)
                    if m is not None:
                        # perform conditional checks
                        if conditionals is not None:
                            for field in conditionals:
                                if m.lastindex >= int(field):
                                    for check in conditionals[field]:
                                        if '$eq' in check:
                                            if m.group(int(field)) != conditionals[field]['$eq']:
                                                ids.append(md.doc['_id'])
                                        elif '$gte' in check:
                                            if m.group(int(field)) < conditionals[field]['$gte']:
                                                ids.append(md.doc['_id'])
                                        elif '$lte' in check:
                                            if m.group(int(field)) > conditionals[field]['$lte']:
                                                ids.append(md.doc['_id'])
                                        elif '$regex' in check:
                                            match = re.match(check['$regex'], field)
                                            if match is None:
                                                ids.append(md.doc['_id'])
                        else:
                            # that we're here IS the conditional ;)
                            ids.append(md.doc['_id'])
        return {'ok': True, 'payload': {'pass': len(ids) == 0, 'ids': ids}}

    @classmethod
    def testDiskReadahead(cls, groupMdiag):
        # rw   256   512  4096          0    8650752  /dev/sda
        # NOTE can also use read_ahead_kb section
        section = "blockdev"
        match = "^\\S+\\s+(\\d+).*(\\/.*)"
        conds = { "1": { "$lte": 64 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testRedhatVersion57(cls, groupMdiag):
        # NOTE can also use distro section
        section = "/etc/system-release"
        match = "Red Hat.+\\s(\\d+\\.\\d+)\\s"
        conds = { "1": { "$gte": 5.7 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testSuseVersion11(cls, groupMdiag):
        # NOTE can also use distro section
        section = "/etc/system-release"
        match = "SUSE.+\\s(\\d+)\\s"
        conds = { "1": { "$gte": 11 } }
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testDmesg(cls, groupMdiag):
        section = "dmesg"
        match = "error|fail|warn|blocked"
        conds = None
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testVmwareBallooning(cls, groupMdiag):
        # vmware_balloon 7199 0 - Live 0xffffffffa0016000
        section = "procinfo"
        match = "vmware_balloon.*Live"
        conds = None
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testSwapInProcSwaps(cls, groupMdiag):
        section = "proc/swaps"
        match = "/dev"
        conds = None
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testSwapInProcSwaps(cls, groupMdiag):
        section = "proc/swaps"
        match = "/dev"
        conds = None
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)

    @classmethod
    def testSwapInEtcFstab(cls, groupMdiag):
        # NOTE can also check in section mount,fstab
        section = "etc/fstab"
        match = "\\sswap\\s"
        conds = None
        return cls._sectionMatchConditionals(groupMdiag, section, match, conds)
