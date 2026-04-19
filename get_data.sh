#!/usr/bin/env bash
#chmod +x get_data.sh

echo "getting the data"
cd data
curl -O "https://zenodo.org/records/14767363/files/2024.zip?download=1" & #EPA 
curl -O "https://zenodo.org/records/8170242/files/3d_1400.hdf5?download=1" & #HDF5 FILE 1
curl -O "https://zenodo.org/records/8170242/files/3d_500a.hdf5?download=1" & #HDF5 FILE 2
curl -O "https://zenodo.org/records/8170242/files/demo.ipynb?download=1" & #Demo
curl -O "https://zenodo.org/records/8170242/files/LICENSE?download=1" & #License
curl -O "https://zenodo.org/records/8170242/files/loh.hdf5?download=1" & #HDF5 FILE 3
curl -O "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gzm" & # Clin Var
curl -O "https://data.cdc.gov/api/v3/views/k9zj-b28y/query.csv" & # CDC Data

