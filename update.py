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


import urllib3
import time
from itertools import chain
import lxml.html
import xml.etree.ElementTree as ET
import certifi
import sqlite3
import sys
from logging import getLogger
from logging import FileHandler
from logging import StreamHandler
from logging import INFO
from logging import basicConfig
from logging import Formatter

import constants
import iterator_tools

stream_logger = None
file_logger = None

def replace_table(cursor, table_name, schema_params, tuples):
    # table_name : str
    # schema_params : dict (key: column name, value: type)
    # tuples : tuple list OR tuple iterator OR tuple set OR tuple tuple
    drop_query = "DROP TABLE IF EXISTS %s" % table_name
    cursor.execute(drop_query)

    create_query = "CREATE TABLE IF NOT EXISTS %s (%s)" % (
            table_name,
            ", ".join(
                ("%s %s" % t for t in schema_params))
            )
    cursor.execute(create_query)

    insert_query = "INSERT INTO %s VALUES (%s)" % (
            table_name,
            ", ".join(
                ("?" for i in range(len(schema_params))))
            # "? ? ... ?" (r"(\? ){n-1}\?")
            # n: number of parameters
            )
    cursor.executemany(insert_query, tuples)

def map_with_sleep(f, iterator, second=1):
    # If type of iterator is not iterator, it will be converted to iterator.
    if any(isinstance(iterator, c) for c in [list, set, tuple]):
        iterator = iter(iterator)

    yield f(next(iterator))
    for item in iterator:
        time.sleep(second)
        yield f(item)

def get_data_online(method, url, params):
    method_set = {"GET", "POST"}
    if method not in method_set:
        return None

    with urllib3.PoolManager(
            cert_reqs = "CERT_REQUIRED",
            ca_certs = certifi.where()
            ) as http:
        stream_logger.info("Access to %s" % url)
        file_logger.info("Access to %s" % url)
        r = http.request(method, url, fields=params)
        data = r.data.decode()

    return data

def get_mito_id_gene_id_pairs():
    # Collect Mito IDs and Gene IDs of genes recorded in [MitoProteome](http://www.mitoproteome.org).
    params = {
            "nums" : "10000",
            }
    data = get_data_online("POST", constants.mito_table_url, params)
    root = lxml.html.fromstring(data)
    anchors = root.xpath("//a")
    mito_id_anchors = filter(
            lambda anchor:
            constants.mito_detail_php in anchor.attrib["href"],
            anchors
            )
    gene_id_anchors = filter(
            lambda anchor:
            constants.entrez_gene_record_url in anchor.attrib["href"],
            anchors
            )
    mito_ids = map(lambda anchor: anchor.text, mito_id_anchors)
    gene_ids = map(lambda anchor: anchor.text, gene_id_anchors)
    return zip(mito_ids, gene_ids)


def get_uniprot_info(accs):
    # Map each UniProt AC to the following things:
    #   * protein names
    #   * gene names
    #   * organism
    columns = [
            "id",
            "entry",
            "protein names",
            "genes",
            "organism",
            ]
    params = {
            "query" : " OR ".join(
                map(lambda s:
                    "accession:" + s,
                    accs
                    )
                ),
            "columns" : ",".join(columns),
            "format" : "tab",
            }
    data = get_data_online("GET", constants.uniprot_url, params)
    info_lines = data.split("\n")[1:]
    return filter(
            lambda t:
            len(t) == 4,
            map(lambda s: tuple(s.split("\t")), info_lines)
            )

    # return (UniProt AC, protein names, gene names, organism)
    #
    # for example; ('P53396',
    #               'ATP-citrate synthase (EC 2.3.3.8) \
    #                   (ATP-citrate (pro-S-)-lyase) (ACL)
    #                   (Citrate cleavage enzyme)',
    #               'ACLY',
    #               'Homo sapiens (Human)')

def map_id(iterator, from_abbrev, to_abbrev):
    params = {
            "from" : from_abbrev,
            "to" : to_abbrev,
            "format" : "tab",
            "query" : ",".join(iterator),
            }
    data = get_data_online("GET", constants.uniprot_mapping_url, params).strip()
    info_line = data.split("\n")[1:]
    return filter(
            lambda t:
            len(t) == 2,
            map(lambda s: tuple(s.split("\t")), info_line)
            )

def get_with_sleep(f, iterator, group_n=100):
    # Take sleep in order to avoid server overload
    #
    # Split iterator in order to reduce data traffic per connection
    return iterator_tools.concat_iterator(
            *map_with_sleep(f, iterator_tools.split_iterator(iterator, group_n)))

def get_uniprot_acs(gene_ids):
    # Map Gene IDs to UniProt ACs.
    return map_id(gene_ids, "P_ENTREZGENEID", "ACC")

def get_pdb_ids(accs):
    # Map each UniProt AC to PDB ID
    return map_id(accs, "ACC", "PDB_ID")

def get_kegg_id(accs):
    # Map each UniProt AC to KEGG ID
    return map_id(accs, "ACC", "KEGG_ID")

def get_pdb_info(pdb_ids):
    # Get the following things of each PDB ID:
    #   * resolution
    #   * entity ID
    #   * chain ID
    url = constants.pdb_rest_url + "getEntityInfo"
    params = {
            "structureId" : ",".join(pdb_ids),
            }
    xmldata = get_data_online("GET", url, params)
    tree = ET.fromstring(xmldata)
    pdb_nodes = tree.findall("PDB")
    methods = map(
            lambda node:
            node.find("Method").attrib["name"],
            pdb_nodes
            )
    resolutions = map(
            lambda node, method:
            node.attrib["resolution"] if (method == "xray" and "resolution" in set(node.attrib.keys())) else None,
            pdb_nodes,
            methods
            )
    pdb_ids = map(lambda node: node.attrib["structureId"], pdb_nodes)
    entities = map(lambda node: node.findall("Entity"), pdb_nodes)
    #protein_entities = ((e for e in elist if e.attrib["type"] == "protein") for elist in entities)
    protein_entities = map(
            lambda elist:
            filter(lambda e:
                e.attrib["type"] == "protein",
                elist
                ),
            entities
            )
    entity_ids = map(
            lambda elist:
            [(e.attrib["id"],
                [n.attrib["id"] for n in e.findall("Chain")])
                for e in elist],
            protein_entities
            )
    return zip(pdb_ids, resolutions, entity_ids)

def get_chain_info(chains):
    # Get the following things of PDB chain:
    #   * length of chain
    #   * accession (UniProt AC)
    # chains is like [("1JU5", "C"), ("2BID", "A"), ...] (iterator is OK).
    url = constants.pdb_rest_url + "describeMol"
    params = {
            "structureId" : ",".join(
                map(lambda t: # t = (pdb_id, chain_id)
                    t[0] + "." + t[1], # pdb_id + "." + chain_id
                    chains
                    )
                ),
            }
    xmldata = get_data_online("GET", url, params)
    tree = ET.fromstring(xmldata)
    structureId_nodes = tree.findall("structureId")
    tuples = map(
            lambda node:
            (node.attrib["id"], # PDB ID
                node.attrib["chainId"], # chain ID
                node.find("polymer").attrib["length"], # length
                (node.find("polymer")
                    .find("macroMolecule")
                    ) # macroMolecule's node or None
                ),
            structureId_nodes
            )
    return map(
            lambda t: # t = (PDB ID, chain ID, length, node or None)
            (t[0], t[1], t[2],
                t[3].find("accession").attrib["id"] if t[3] != None else None),
            tuples
            )


def update_sqlite3db():
    global stream_logger
    global file_logger
    stream_logger = getLogger("stream")
    file_logger = getLogger("file")
    stream_handler = StreamHandler(stream=sys.stdout)
    file_handler = FileHandler(constants.logfile)
    logformat = Formatter(
            "[%(asctime)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
            )
    stream_handler.setFormatter(logformat)
    file_handler.setFormatter(logformat)
    stream_logger.addHandler(stream_handler)
    file_logger.addHandler(file_handler)
    stream_logger.setLevel(INFO)
    file_logger.setLevel(INFO)

    mitoproteome_tuples = get_mito_id_gene_id_pairs()

    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            table_name = "mitoproteome"
            schema_params = [
                    ("mito_id", "TEXT"),
                    ("gene_id", "INTEGER"),
                    ]
            tuples = mitoproteome_tuples
            replace_table(cursor, table_name, schema_params, tuples)

            select_query = \
                    "SELECT DISTINCT gene_id \
                    FROM mitoproteome"
            results = cursor.execute(select_query)

            conn.commit()
    except sqlite3.Error as e:
        # print("ERROR at mitoproteome")
        sys.stderr.write("%s\n" % e)
        quit(1)

    gene_ids = map(lambda p: str(p[0]), results)
    gene_id_uniprot_ac_pairs = get_with_sleep(get_uniprot_acs, gene_ids)

    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            table_name = "gene_uniprot"
            schema_params = [
                    ("gene_id", "INTEGER"),
                    ("uniprot_ac", "TEXT"),
                    ]
            tuples = gene_id_uniprot_ac_pairs
            replace_table(cursor, table_name, schema_params, tuples)

            select_query = \
                    "SELECT DISTINCT uniprot_ac \
                    FROM gene_uniprot"
            results = cursor.execute(select_query)

            conn.commit()
    except sqlite3.Error as e:
        # print("ERROR at entrez_gene")
        sys.stderr.write("%s\n" % e)
        quit(1)

    uniprot_ac_list = [p[0] for p in results]

    uniprot_infos = get_with_sleep(get_uniprot_info, uniprot_ac_list)
    uniprot_ac_pdb_id_pairs = get_with_sleep(get_pdb_ids, uniprot_ac_list)
    uniprot_ac_kegg_id_pairs = get_with_sleep(get_kegg_id, uniprot_ac_list)

    del uniprot_ac_list

    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            table_name = "uniprot_info"
            schema_params = [
                    ("uniprot_ac", "TEXT"),
                    ("protein_names", "TEXT"),
                    ("gene_names", "TEXT"),
                    ("organism", "TEXT"),
                    ]
            tuples = uniprot_infos
            replace_table(cursor, table_name, schema_params, tuples)

            table_name = "uniprot_pdb"
            schema_params = [
                    ("uniprot_ac", "TEXT"),
                    ("pdb_id", "TEXT"),
                    ]
            tuples = uniprot_ac_pdb_id_pairs
            replace_table(cursor, table_name, schema_params, tuples)

            table_name = "uniprot_kegg"
            schema_params = [
                    ("uniprot_ac", "TEXT"),
                    ("kegg_id", "TEXT"),
                    ]
            tuples = uniprot_ac_kegg_id_pairs
            replace_table(cursor, table_name, schema_params, tuples)

            select_query = \
                    "SELECT DISTINCT pdb_id \
                    FROM uniprot_pdb"
            results = cursor.execute(select_query)

            conn.commit()
    except sqlite3.Error as e:
        # print("ERROR at uniprot")
        sys.stderr.write("%s\n" % e)
        quit(1)

    pdb_ids = map(lambda p: p[0], results)
    pdb_infos = get_with_sleep(get_pdb_info, pdb_ids)

    pdb_info_tuples = iterator_tools.concat_iterator(
            *iterator_tools.concat_iterator(
                *map(lambda t:
                    # t = (PDB ID,
                    #      resolution,
                    #      [(entity ID, [chain ID ...]) ...])
                    map(lambda lt:    # l = (entity ID, [chain ID ...])
                        map(lambda c: # c is chain ID
                            (t[0], t[1], lt[0], c),
                            # (PDB ID, resolution, entity ID, chain ID)
                            lt[1] # [chain ID ...]
                            ),
                        # [(PDB ID, resolution, entity ID, chain ID) ...]
                        t[2] # [(entity ID, [chain ID ...]) ...]
                        ),
                    # [[(PDB ID, resolution, entity ID, chain ID) ...] ...]
                    pdb_infos
                    # [(PDB ID,
                    #   resolution,
                    #   [(entity ID, [chain ID ...]) ...]) ...]
                    )
                # [[[(PDB ID, resolution, entity ID, chain ID) ...] ...] ...]
                ) # [[(PDB ID, resolution, entity ID, chain ID) ...] ...]
            )     # [(PDB ID, resolution, entity ID, chain ID) ...]
    # pdb_info_tuples = [(PDB ID, resolution, entity ID, chain ID) ...]

    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            table_name = "pdb_info"
            schema_params = [
                    ("pdb_id", "TEXT"),
                    ("resolution", "REAL"),
                    ("entity_id", "INTEGER"),
                    ("chain_id", "TEXT"),
                    ]
            tuples = pdb_info_tuples
            replace_table(cursor, table_name, schema_params, tuples)

            select_query = \
                    "SELECT DISTINCT pdb_id, chain_id \
                    FROM pdb_info"
            results = cursor.execute(select_query)

            conn.commit()
    except sqlite3.Error as e:
        # print("ERROR at PDB")
        sys.stderr.write("%s\n" % e)
        quit(1)

    chain_infos = get_with_sleep(get_chain_info, results)

    try:
        with sqlite3.connect(constants.sqlite3_dbpath) as conn:
            cursor = conn.cursor()
            table_name = "chain_info"
            schema_params = [
                    ("pdb_id", "TEXT"),
                    ("chain_id", "TEXT"),
                    ("length", "INTEGER"),
                    ("uniprot_ac", "TEXT"),
                    ]
            tuples = chain_infos
            replace_table(cursor, table_name, schema_params, tuples)

            conn.commit()
    except sqlite3.Error as e:
        # print("ERROR at chain")
        sys.stderr.write("%s\n" % e)
        quit(1)

    print("Update finished.")
    stream_handler.flush()
    file_handler.close()
