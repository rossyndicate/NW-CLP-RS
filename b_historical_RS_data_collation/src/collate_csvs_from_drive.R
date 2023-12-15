#' @title Collate downloaded csv files into a feather file
#' 
#' @description
#' Function to grab all downloaded .csv files from the b_.../in/ folder with a specific
#' file prefix, collate them into a .feather files with version identifiers
#'
#' @param file_prefix specified string that matches the file group to collate
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' @returns list of feather files created by this function. This function  
#' collates all .csv's containing the file_prefix, and saves up to 4 files
#' by type of data summarized within the file (polygon, point, center). The types
#' of data are automatically detected. Data type is created in the config.yml 
#' file of the associated Landsat-C2-SRST branch. 
#' 
#' @notes for a reason I do not understand, map_dfr creates duplicates of rows
#' sometimes up to 4 times. Each of the collations in this funciton (to all_meta,
#' all_points, etc) run a distinct() function that dramatically reduces the number 
#' of rows.
#' 
#' 
collate_csvs_from_drive <- function(file_prefix, version_identifier) {
  # get the list of files in the `in` directory 
  files <- list.files(file.path("b_historical_RS_data_collation/in/",
                                version_identifier),
                     pattern = file_prefix,
                     full.names = TRUE) 
  
  meta_files <- files[grepl("meta", files)]
  all_meta <- map_dfr(meta_files, read_csv) %>% 
    distinct()
  write_feather(all_meta, file.path("b_historical_RS_data_collation/mid/",
                                  paste0(file_prefix, "_collated_metadata_",
                                         version_identifier, ".feather")))
  
  # if point data are present, subset those, collate, and save
  if (any(grepl("point", files))) {
    point_files <- files[grepl("point", files)]
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_points <- map_dfr(.x = point_files, 
                         .f = function(.x) {
                           read_csv(.x) %>% mutate(source = .x)
                           }) %>% 
      distinct(across(-"source"), .keep_all = TRUE)
    write_feather(all_points, file.path("b_historical_RS_data_collation/mid/",
                                    paste0(file_prefix, "_collated_points_",
                                           version_identifier, ".feather")))
  }
  
  # if centers data are present, subset those, collate, and save
  if (any(grepl("center", files))) {
    center_files <- files[grepl("center", files)]
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_centers <- map_dfr(.x = center_files, 
                         .f = function(.x) {
                           read_csv(.x) %>% mutate(source = .x)
                         }) %>% 
      distinct(across(-"source"), .keep_all = TRUE)
    write_feather(all_centers, file.path("b_historical_RS_data_collation/mid/",
                                    paste0(file_prefix, "_collated_centers_",
                                           version_identifier, ".feather")))
  }
  
  #if polygon data are present, subset those, collate, and save
  if (any(grepl("poly", files))) {
    poly_files <- files[grepl("poly", files)]
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_polys <- map_dfr(.x = poly_files,
                         .f = function(.x) {
                           read_csv(.x) %>% mutate(source = .x)
                         }) %>% 
      distinct(across(-"source"), .keep_all = TRUE)
    write_feather(all_polys, file.path("b_historical_RS_data_collation/mid/",
                                  paste0(file_prefix, "_collated_polygons_",
                                         version_identifier, ".feather")))
  }
  
  # return the list of files from this process
  list.files("b_historical_RS_data_collation/mid/",
                         pattern = file_prefix,
                         full.names = TRUE) %>% 
    #but make sure they are the specified version
    .[grepl(version_identifier, .)]
}