import argparse
import logging
import os
import sys


class ConfigArgumentParser(argparse.ArgumentParser):
    """ An ArgumentParser wrapper that converts each line of a config file into
    an argument to be parsed by the ArgumentParser """
    def __init__(self, *args, **kwargs):
        super(ConfigArgumentParser, self).__init__(*args, **kwargs)

    def convert_arg_line_to_args(self, line):
        args = line.split()
        for i in range(len(args)):
            if i == 0:
                # ignore commented lines
                if args[i][0] == '#':
                    break
                if not args[i].startswith('--'):
                    # add '--' to simulate cli option
                    args[i] = "--%s" % args[i]
            # ignore blanks
            if not args[i].strip():
                continue

            yield args[i]


class CliArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        """ Process command line arguments with a system of tubes """
        # This is a non-positional argument parser that can be used for
        # --config processing
        self.parser = argparse.ArgumentParser(*args, **kwargs)
        self.parser.add_argument("--config", metavar="FILE",
                                 help="specify a configuration file")
        self.parser.add_argument("--log", metavar="FILE",
                                 help="specify a log file")
        self.parser.add_argument("--log-level", metavar="LEVEL",
                                 choices=["DEBUG", "INFO", "WARNING", "ERROR",
                                          "CRITICAL"],
                                 default="INFO",
                                 help="{DEBUG,INFO,WARNING,ERROR,CRITICAL} "
                                      "(default=INFO)")

        # Save in case they are needed for reinitialization
        self.kwargs = kwargs
        self.kwargs['add_help'] = False
        self.kwargs['parents'] = [self.parser]
        argparse.ArgumentParser.__init__(self, *args, **self.kwargs)

    def add_config_argument(self, *args, **kwargs):
        # Modifying parent parser requires reinitialization
        self.parser.add_argument(*args, **kwargs)
        argparse.ArgumentParser.__init__(self, **self.kwargs)

    def parse_args(self):
        if len(sys.argv) == 1:
            # n00bs need help!
            args = argparse.ArgumentParser.parse_args(self, ['--help'])
        else:
            args = argparse.ArgumentParser.parse_args(self)

        # Configuration error found, aborting
        error = False

        # Process config file if one is specified in the cli options
        if args.config is not None:
            args.config = os.path.abspath(os.path.expandvars(
                os.path.expanduser(args.config)))
            if os.access(args.config, os.R_OK):
                configParser = ConfigArgumentParser(add_help=False,
                                                    fromfile_prefix_chars='@',
                                                    parents=[self.parser])
                args = configParser.parse_args(args=["@%s" % args.config],
                                               namespace=args)
            else:
                logging.error("Unable to read config file")
                error = True

        # I pity the fool who doesn't keep a log file!
        if args.log is not None:
            args.log = os.path.abspath(os.path.expandvars(os.path.expanduser(
                args.log)))
            if not os.access(os.path.dirname(args.log), os.W_OK):
                logging.error("Unable to write to log file")
                error = True

        if error:
            sys.exit(2)

        return args
