# NW-CLP-RS

Generalized repository for Northern and Cache La Poudre lakes and reservoir 
remote sensing pulls and collation.

Primary repository contact: B Steele <b dot steele at colostate dot edu>

This repository is covered by the MIT use license. We request that all 
downstream uses of this work be available to the public when possible.

## Important notes:

- This repository uses a symlink data folder to the NASA-NW OneDrive data folder. 
Contact B for the link to this if needed.

- We recommend running the {targets} workflow from the run_targets.Rmd file.

- In order to use this workflow, you must have a [Google Earth Engine account](https://earthengine.google.com/signup/) 
and have configured a [Google Cloud Project](https://developers.google.com/earth-engine/cloud/projects) 
and you will need to [download, install, and initialize gcloud](https://cloud.google.com/sdk/docs/install). 

- The Earth Engine workflow has been modified from the [Landsat_C2_SRST_template](https://github.com/rossyndicate/Landsat_C2_SRST_template)
to be able to run the ee workflow in multiple subfolders without issues with 
{targets} or Earth Engine.

## Confirm `gcloud` function:

It is recommended to run the following command in your **zsh** terminal and 
follow the prompts in  your browser to ensure that your gcloud is set up correctly.

`earthengine authenticate`

Follow the prompts in your browser. When completed in the browser, your terminal 
will also read:

`Successfully saved authorization token.`

This token is valid for 7 days from the time of authentication. If this fails,
see the [common issues](https://github.com/rossyndicate/ROSS_RS_mini_tools/blob/main/helps/CommonIssues.md) or contact B for help troubleshooting.

------------------------------------------------------------------------

## {targets} architecture overview

This targets workflow is broken down into groups of target lists that perform 
functional chunks of the workflow.


_a_locs_poly_setup_:

This group sets up the locations and polygon files 
for RS retrieval. The group of functions collates a few different polygon and 
point files into a single file of each type as needed for the RS workflow.


_b_site_RS_data_acquisition_:

This group of targets acquires the Landsat record for our focus lakes as part of 
the Northern Water project, our internal Cache La Poudre lakes, as well as all
lakes greater than 1 hectare in the CLP HUC12. This group of targets also collates
the files of this pull and adds the metadata to create a singular file per extent
and DSWE. In this case, we are only pulling sites and lake centers for DSWE1 
(confident water).


_c_regional_RS_data_acquisition_:

Similar to group -b-, this targets group acquires the Landsat record, but for all
lakes greater than 1 hectare for lakes that fall within the EcoRegion Level 3 Zone
21 area. These data are used to calculate handoff calculations on a regional level, 
which we suspect may be better than a national handoff coefficient (e.g. all lakes
across the US), since we assume that atmospheric correction processes likely have
ingrained processes (or biases) based on general location (e.g. elevation, distance
to ocean). At some point in the future, we will likely compare the coefficients 
here to those calculated by the Gardener lab (focused on the east coast) and those
from lakeSR (calculated across all US and territories).



_d_calculate_handoff_coefficients_:

This group of functions calculates the inter-mission handoff coefficients from 
the regional pull data. Landsat 4-7 and 8-9 surface reflectance data go through 
two different atmospheric corrections (LEDAPS and LaSRC). Additionally, each 
band wavelength can vary between missions. This script uses an adapted version 
of the methods in Topp, et al. 2021 to correct for each satellite handoff, 
correction to LS 7 values. Additionally, a handoff for Landsat 7 and 9 is 
calculated to harmonize to LS 8 values for workflows that do not require the 
entire LS record. The LS 9 to LS 8 handoffs include calculations for the Aerosol 
band, which may be useful for workflows that only use LS 8 & 9.


_e_apply_handoff_coefficients_:

This group of functions applies the handoff coefficients to dataset(s), flags
for band values outside of the handoff inputs that created the correction
coefficients, and saves the analysis-ready file(s). Additionally, figures are
created to compare the raw, LS7-corrected, and LS8-corrected figures.


_f_separate_NW_CLP_data_:

This group of functions splits the data for individual research programs and 
stores them in the ROSS Google Drive.

