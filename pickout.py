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

import sqlite3

import constants


def retrieve_all_data():
    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            query = (
                    "CREATE VIEW IF NOT EXISTS protein_csv AS\n"
                    "SELECT DISTINCT pdb_info.pdb_id, "
                    "chain_info.chain_id, uniprot_info.uniprot_ac, "
                    "uniprot_info.protein_names, uniprot_info.gene_names, "
                    "uniprot_info.organism, uniprot_kegg.kegg_id, "
                    "mitoproteome.mito_id, gene_uniprot.gene_id\n"
                    "FROM pdb_info, chain_info, uniprot_info, uniprot_pdb, "
                    "uniprot_kegg, mitoproteome, gene_uniprot\n"
                    "WHERE mitoproteome.gene_id = gene_uniprot.gene_id\n"
                    "AND gene_uniprot.uniprot_ac = uniprot_info.uniprot_ac\n"
                    "AND gene_uniprot.uniprot_ac = uniprot_pdb.uniprot_ac\n"
                    "AND gene_uniprot.uniprot_ac = uniprot_kegg.uniprot_ac\n"
                    "AND (SUBSTR(uniprot_kegg.kegg_id, 4, 1) = ':' AND "
                    "SUBSTR(uniprot_kegg.kegg_id, 5) = gene_uniprot.gene_id OR "
                    "SUBSTR(uniprot_kegg.kegg_id, 5, 1) = ':' AND "
                    "SUBSTR(uniprot_kegg.kegg_id, 6) = gene_uniprot.gene_id)\n"
                    "AND uniprot_pdb.pdb_id = pdb_info.pdb_id\n"
                    "AND pdb_info.pdb_id = chain_info.pdb_id\n"
                    "AND pdb_info.chain_id = chain_info.chain_id\n"
                    "AND chain_info.uniprot_ac = uniprot_info.uniprot_ac"
                    )
            # view name: protein_csv
            #
            # columns:
            #
            # pdb_id | chain_id | uniprot_ac | protein_names | gene_names | organism | kegg_id | mito_id | gene_id
            # -------+----------+------------+---------------+------------+----------+---------+---------+--------

            cursor.execute(query)
            query = "SELECT DISTINCT * FROM protein_csv"
            results = cursor.execute(query)

            # conn.commit() # <- Is it necessary to write this line?
    except sqlite3.Error as e:
        sys.stderr.write("%s\n" % e)
        quit(1)

    return results

def pickout_data(chain_list):
    results = retrieve_all_data()
    chain_list = [tuple(s.split("_")) for s in set(chain_list)]
    return filter(lambda t: (t[0], t[1]) in chain_list, results)
