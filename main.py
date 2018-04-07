#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# written in Python3


# MIT License
#
# Copyright (c) 2018 Hiroki Watanabe
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse

import update
import pickout


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="MP-manager is the mitochondrial protein's CSV file manager.",
            formatter_class=argparse.RawTextHelpFormatter
            )
    subparsers = parser.add_subparsers(
            dest="command",
            )
    parser_update = subparsers.add_parser(
            "update",
            description="update sqlite3 database",
            help="update sqlite3 database"
            )
    parser_pickout = subparsers.add_parser(
            "pickout",
            description="pick out given proteins' information",
            help="pick out given proteins' information"
            )
    parser_pickout.add_argument(
            "-d", "--dest",
            help="specify (non-existing) output filename",
            nargs=1
            )
    parser_pickout.add_argument(
            "-a", "--all",
            help="show all proteins' data",
            action="store_true"
            )
    parser_pickout.add_argument(
            "chains",
            help="PDB chain (1A02_A, 10GS_A, etc.) list",
            nargs="*"
            )
    args = parser.parse_args()

    if args.command == "update":
        update.update_sqlite3db()
    elif args.command == "pickout":
        column_names = (
                "pdbid,chain,uniprot,proteinnames,genenames,"
                "organism,kegg,mitoid,entrezgeneid"
                )
        if args.all:
            tuples = pickout.retrieve_all_data()
        else:
            tuples = pickout.pickout_data(args.chains)

        if args.dest == None:
            print(column_names)
            for t in tuples:
                print("%s,%s,%s,%s,%s,%s,%s,%s,%s" % t)
        else:
            filename = args.dest[0]
            if os.path.exists(filename):
                sys.stderr.write("%s exists!\n"
                                 "exit\n" % filename)
                quit(1)

            with open(filename, "w") as f:
                f.write("%s\n" % column_names)
                for t in tuples:
                    f.write("%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % t)
    else:
        parser.print_help()
