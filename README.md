# aufs
AUFS is a metadata fabric file system layer

Provisioning.

Apache Parquet.
Immutable.
Schema.
Data.
Metadata.

Provisioning.

owner...a data's owner provisions.
custodian...storage owners facilitate provisioning.



Parquet schema and it's dictionaries & metadata describe the dir tree. They also 
explain how to get the tree made. Once thats done the remaining metadata+dictionaries will
point towards the table chunk from which the data provisioning
information is pulled. The data owner's setup does its stuff from here!
