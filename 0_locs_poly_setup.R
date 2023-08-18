# Source funcitons for this {targets} list
tar_source('0_locs_poly_setup/src/')

p0_targets_list <- list(
  # get the polygons for CLP watershed using HUC8
  tar_target(
    name = p0_make_CLP_polygon,
    command = get_polygons('10190007', 0.01),
    packages = c('sf', 'nhdplusTools', 'tidyverse')
  ),
  # track and load the CLP polygons
  tar_file_read(
    name = p0_CLP_polygons,
    command = p0_make_CLP_polygon,
    read = read_sf(!!.x),
    packages = 'sf'
  ),
  # track and load the csv with NW locs
  tar_file_read(
    name = p0_NW_locs_file,
    command = 'data/spatialData/ReservoirLocations.csv',
    read = read_csv(!!.x),
    packages = 'readr'
  ),
  tar_target(
    name = p0_get_NW_hucs,
    command = get_hucs_from_points(p0_NW_locs_file, 'EPSG:4326'),
    packages = c('sf', 'nhdplusTools', 'tidyverse')
  ),
  tar_target(
    name = p0_get_NW_wbd,
    command = get_polygons(p0_get_NW_hucs, 0.1),
    pattern = map(p0_get_NW_hucs)
  )
)
# ,
#   tar_target(
#     name = p0_make_NW_polygon,
#     command = get_polygons_from_pts(p0_get_NW_wbd, NA_real_),
#     packages = c('sf', 'nhdplusTools', 'tidyverse'),
#     pattern = p0_get_NW_hucs
#   )
# )