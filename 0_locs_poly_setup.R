# Source funcitons for this {targets} list
tar_source('0_locs_poly_setup/src/')

p0_targets_list <- list(
  tar_target(
    name = p0_make_CLP_polygon,
    command = get_polygons('10190007', 'HR', 0.01),
    packages = c('sf', 'nhdplusTools')
  ),
  tar_file_read(
    name = p0_CLP_polygons,
    command = tar_read(p0_make_CLP_polygon),
    read = read_sf(!!.x),
    packages = "sf"
  )
)