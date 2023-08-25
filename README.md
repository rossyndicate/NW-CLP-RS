# NW-CLP-RS

Generalized repository for Northern and Cache La Poudre lakes and reservoir 
remote sensing pulls and collation.

Primary repository contact: B Steele <b dot steele at colostate dot edu>

This repository is covered by the MIT use license. We request that all 
downstream uses of this work be available to the public when possible.


### Important notes: 

This repository uses a symlink data folder to the NASA-NW OneDrive data folder. 
Contact B for the link to this if needed. 

This workflow incorporates environment settings within an .Renviron document. This 
document is not tracked in GH. Please request this file from B. 


### {targets} architecture overview

This targets workflow is broken down into groups of target lists that perform
functional chunks of the workflow.

__p0: 0_locs_poly_setup__
This group sets up the locations and polygon files for RS retrieval. The group 
of funcitons collates a few different polygon and point files into a single
file of each type as needed for the RS workflow. 

__p1: 1_historical_RS_data_collation__
This group of functions downloads and processes GEE output from historical pulls.
This portion of the workflow is dependent on the successful run of two 
branches of the Landsat_C2_SRST repository: nw-poudre-historical and 
nw-er3z21-historical. At this time, this is run outside of the {targets} workflow 
presented here. 
