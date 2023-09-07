# NW-CLP-RS

Generalized repository for Northern and Cache La Poudre lakes and reservoir 
remote sensing pulls and collation.

Primary repository contact: B Steele <b dot steele at colostate dot edu>

This repository is covered by the MIT use license. We request that all 
downstream uses of this work be available to the public when possible.

### Important notes:

This repository uses a symlink data folder to the NASA-NW OneDrive data folder. 
Contact B for the link to this if needed.

This workflow incorporates environment settings within an .Renviron document. 
This document is not tracked in GH. Please request this file from B.

------------------------------------------------------------------------

## {targets} architecture overview

This targets workflow is broken down into groups of target lists that perform 
functional chunks of the workflow.

__a_locs_poly_setup__

This group sets up the locations and polygon files 
for RS retrieval. The group of functioons collates a few different polygon and 
point files into a single file of each type as needed for the RS workflow.

__b_historical_RS_data_collation__

This group of functions downloads and 
processes GEE output from historical pulls. This portion of the workflow is 
dependent on the successful run of two branches of the Landsat_C2_SRST 
repository: nw-poudre-historical and nw-er3z21-historical. At this time, this 
is run outside of the {targets} workflow presented here.

__c_calculate_handoff_coefficients__

This group of functions calculates the inter-mission handoff coefficients from 
the regional pull data. Landsat 4-7 and 8-9 surface reflectance data go through 
two different atmospheric corrections (LEDAPS and LaSRC). Additionally, each 
band wavelength can vary between missions. This script uses an adapted version 
of the methods in Topp, et al. 2021 to correct for each satellite handoff, 
correction to LS 7 values. Additionally, a handoff for Landsat 7 and 9 is 
calculated to harmonize to LS 8 values for workflows that do not require the 
entire LS record. The LS 9 to LS 8 handoffs include calculations for the Aerosol 
band, which may be useful for workflows that only use LS 8 & 9.
