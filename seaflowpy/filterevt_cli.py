#!/usr/bin/env python
import argparse
import botocore
import clouds
import conf
import db
import evt
import filterevt
import json
import pkg_resources
import sys


def parse_args(args):
    version = pkg_resources.get_distribution("seaflowpy").version

    p = argparse.ArgumentParser(
        description="A program to filter EVT data (version %s)" % version,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument("-e", "--evt_dir", metavar="DIR",
                   help="EVT directory path (required unless --s3)")
    p.add_argument("-s", "--s3", default=False, action="store_true",
                   help="""Read EVT files from s3://S3_BUCKET/CRUISE where
                   CRUISE is provided by --cruise (required unless
                   --evt_dir)""")
    p.add_argument("-l", "--limit", type=int, default=None, metavar="N",
                   help="""Limit how many files to process. Useful for testing.
                   (optional)""")

    p.add_argument("-d", "--db", required=True, metavar="FILE",
                   help="""SQLite3 db file. (required)""")
    p.add_argument("-o", "--opp_dir", metavar="DIR",
                   help="""Directory in which to save LabView binary formatted
                   files of focused particles (OPP). Will be created
                   if does not exist. (optional)""")

    p.add_argument("-c", "--cruise", required=True, metavar="NAME",
                   help="Cruise name (required)")
    p.add_argument("--notch1", type=float, metavar="N",
                   help="Notch 1 (optional)")
    p.add_argument("--notch2", type=float, metavar="N",
                   help="Notch 2 (optional)")
    p.add_argument("--width", type=float, default=1.0, metavar="N",
                   help="Width (optional)")
    p.add_argument("--origin", type=float, metavar="N",
                   help="Origin (optional)")
    p.add_argument("--offset", type=float, default=0.0, metavar="N",
                   help="Offset (optional)")
    p.add_argument("-t", "--twopass", default=False, action="store_true",
                   help="""Perform two-pass filter process to autocalculate
                   parameters.""")

    p.add_argument("-p", "--process_count", required=False, type=int, default=1,
                   metavar="N", help="""Number of processes to use in filtering
                   (optional)""")
    p.add_argument("-r", "--resolution", type=float, default=10.0, metavar="N",
                   help="Progress update resolution by %% (optional)")

    p.add_argument("--version", action="version", version="%(prog)s " + version)

    args = p.parse_args(args)

    # Validate args
    if not args.evt_dir and not args.s3:
        sys.stderr.write("Error: One of --evt_dir or --s3 must be provided\n\n")
        p.print_help()
        sys.exit(1)

    return args


def main(cli_args=None):
    """Main function to implement command-line interface"""
    if cli_args is None:
        cli_args = sys.argv[1:]

    args = parse_args(cli_args)

    # Print defined parameters
    v = dict(vars(args))
    to_delete = [k for k in v if v[k] is None]
    for k in to_delete:
        v.pop(k, None)  # Remove undefined parameters
    v["version"] = pkg_resources.get_distribution("seaflowpy").version
    print "Defined parameters:"
    print json.dumps(v, indent=2)
    print ""

    # Find EVT files
    if args.evt_dir:
        files = evt.find_evt_files(args.evt_dir)
    elif args.s3:
        # Make sure configuration for s3 is ready to go
        config = conf.get_aws_config(s3_only=True)
        cloud = clouds.AWS(config.items("aws"))
        # Make sure try to access S3 up front to setup AWS credentials before
        # launching child processes.
        try:
            files = cloud.get_files(args.cruise)
            files = evt.parse_file_list(files)  # Only keep EVT files
        except botocore.exceptions.NoCredentialsError as e:
            print "Please configure aws first:"
            print "  $ conda install aws"
            print "  or"
            print "  $ pip install aws"
            print "  then"
            print "  $ aws configure"
            sys.exit(1)

    # Restrict length of file list with --limit
    if (not args.limit is None) and (args.limit > 0):
        files = files[:args.limit]

    filter_keys = ["notch1", "notch2", "width", "offset", "origin"]
    filter_options = dict((k, getattr(args, k)) for k in filter_keys)

    # Filter
    if args.twopass:
        filterer = filterevt.two_pass_filter
    else:
        filterer = filterevt.filter_evt_files
    filterer(files, args.cruise, filter_options, args.db,
             args.opp_dir, s3=args.s3, process_count=args.process_count,
             every=args.resolution)

    # Index
    if args.db:
        db.ensure_indexes(args.db)


if __name__ == "__main__":
    main()
