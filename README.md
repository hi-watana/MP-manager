# MP-manager

MP-manager is the mitochondrial protein's CSV file manager for the following
purposes:
* collecting scattered information on mitochondrial proteins from several public
  databases
* picking some information out of the collected information in the form of CSV
  format output

__Note__ : In this README.md, "mitochondrial proteins" stands for proteins coded
by the genes recorded in [MitoProteome](http://www.mitoproteome.org), an
object-relational mitochondrial gene/protein sequence database and annotation
system.


### Usage

First, execute the following command:

> $ ./main.py

Usage of this program appears.

To collect information on mitochondrial proteins, execute the following command:

> $ ./main.py update

If sqlite database `protein_info.sqlite3` does not exist in the directory that
contains `main.py`, `protein_info.sqlite3` appears in the directory. It has the
collected information on mitochondrial proteins.
On the other hand, if `protein_info.sqlite` already exists, the data stored in
it is updated.

To pick some information out of the collected information, use `pickout` sub
command. If you want to pick out the information on specific proteins, execute
the following command:

> $ ./main.py pickout \<PDB ID\>\_\<chain ID\> \<PDB ID\>\_\<chain ID\> ...

For, instance, execute the following command:

> $ ./main.py pickout 2VGZ_A 3FCK_A

PDB ID is the 4-character unique identifier (such as 2VGZ, 3FCK) of every entry
in the [Protein Data Bank (PDB)](https://www.rcsb.org/pdb), the single worldwide
archive of structural data of biological macromolecules. The word "chain ID"
(such as A, B) stands for the unique identifier of every chain in a PDB entry.

If you want to get all of the collected information, execute the following
command:

> $ ./main.py pickout --all


### Modules
MP-manager consists of the following modules:
* __constants.py__  
    module that contains constant values
* __iterator_tools.py__  
    module that contains functions to process iterator
* __main.py__  
    main module
* __pickout.py__  
    module for picking some information out of the collected information
* __update.py__  
    module for updating data stored in `protein_info.sqlite3`


### Process of Collecting information

1. Collect Mito IDs and Gene IDs of genes recorded in [MitoProteome](http://www.mitoproteome.org).
1. Map Gene IDs to UniProt ACs. [UniProt](http://www.uniprot.org) is a
   comprehensive resource for protein sequence and annotation data. UniProt AC
   is the unique identifier of every entry in UniProt.
1. Map each UniProt AC to the following things:
    * protein names
    * gene names
    * organism
    * PDB ID
    * KEGG ID
1. Get the following things of each PDB ID:
    * resolution
    * entity ID
    * chain ID
1. Get the following things of each PDB chain:
    * length of chain
    * accession (UniProt AC)


### Detail of tables in protein_info.sqlite3

* `mitoproteome` table:  
   attributes:  
    * `mito_id` (Mito ID)
    * `gene_id` (Gene ID)
* `gene_uniprot` table:  
   attributes:  
    * `gene_id` (Gene ID)
    * `uniprot_ac` (UniProt AC)
* `uniprot_info` table:  
   attributes:  
    * `uniprot_ac` (UniProt AC)
    * `protein_names` (protein names)
    * `gene_names` (gene names)
    * `organism` (organism)
* `uniprot_pdb` table:  
   attributes:  
    * `uniprot_ac` (UniProt AC)
    * `pdb_id` (PDB ID)
* `uniprot_kegg` table:  
   attributes:  
    * `uniprot_ac` (UniProt AC)
    * `kegg_id` (KEGG ID)
* `pdb_info` table:  
   attributes:  
    * `pdb_id` (PDB ID)
    * `resolution` (resolution)
    * `entity_id` (entity ID)
    * `chain_id` (chain ID)
* `chain_info` table:  
   attributes:  
    * `pdb_id` (PDB ID)
    * `chain_id` (chain ID)
    * `length` (length of chain)
    * `uniprot_ac` (UniProt AC)
