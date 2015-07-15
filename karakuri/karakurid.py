#!/usr/bin/env python

import daemon
import karakuriclient
import logging
import os
import pidlockfile
import signal
import sys
import time


class karakurid(karakuriclient.karakuriclient):
    """ A scary karakuri daemon """
    def __init__(self, *args, **kwargs):
        karakuriclient.karakuriclient.__init__(self, *args, **kwargs)

    def run(self):
        while 1:
            self.logger.info("Pruning existing tasks...")
            res = self.queueRequest("prune")
            if res['status'] != "success":
                self.logger.warning(res['message'])
                time.sleep(60)
                continue
            self.logger.info("Finding new tasks...")
            res = self.queueRequest("find")
            if res['status'] != "success":
                self.logger.warning(res['message'])
                time.sleep(60)
                continue
            self.logger.info("Processing approved tasks...")
            res = self.queueRequest("process")
            if res['status'] != "success":
                self.logger.warning(res['message'])
                time.sleep(60)
                continue
            time.sleep(60)

if __name__ == "__main__":
    parser = karakuriclient.karakuriclientparser(description="A scary karakuri"
                                                             " daemon")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/karakurid.pid",
                               help="specify a PID file "
                                    "(default=/tmp/karakurid.pid)")
    parser.add_argument("command", choices=["start", "stop", "restart",
                                            "debug"],
                        help="<-- the available actions, choose one")

    args = parser.parse_args()

    if args.command == "debug":
        # Run un-daemonized
        k = karakurid(args)
        k.run()
        sys.exit(0)

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(3)

    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    fh.setLevel(args.log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Lock it down
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(1)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(2)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # This is daemon territory
    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)
    context.files_preserve = [fh.stream]
    # TODO implment signal_map

    with context:
        k = karakurid(args)
        k.run()
sys.exit(0)
