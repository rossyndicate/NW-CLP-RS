#' @title Collate downloaded csv files into a feather file
#' 
#' @description
#' Function to grab all downloaded .csv files from the data_acquisition/in/ folder with a specific
#' file prefix, collate them into a .feather files with version identifiers
#'
#' @param file_prefix specified string that matches the file group to collate
#' @param version_identifier user-specified string to identify the RS pull these
#' data are associated with
#' @param parent_path parent filepath where the RS run is occurring
#' 
#' @returns list of feather files created by this function. This function  
#' collates all .csv's containing the file_prefix, and saves up to 4 files
#' by type of data summarized within the file (polygon, point, center). The types
#' of data are automatically detected. Data type is created in the config.yml 
#' file of the associated Landsat-C2-SRST branch. 
#' 
#' 
collate_csvs_from_drive <- function(file_prefix, 
                                    version_identifier,
                                    parent_path) {
  
  # get the list of files in the `down` directory 
  files <- list.files(file.path(parent_path,
                                "down",
                                version_identifier),
                      pattern = file_prefix,
                      full.names = TRUE) 
  # also grab the short name for these, to make sure filtering doesn't include
  # full path that may present issues...
  files_short <- list.files(file.path(parent_path,
                                      "down",
                                      version_identifier),
                            pattern = file_prefix,
                            full.names = FALSE) 
  
  meta_files <- files[grepl("meta", files_short)]
  all_meta <- map_dfr(meta_files, read_csv) 
  write_feather(all_meta, file.path(parent_path, 
                                    "mid",
                                    paste0(file_prefix, "_collated_metadata_",
                                           version_identifier, ".feather")))
  
  # if point data are present, subset those, collate, and save
  if (any(grepl("site", files))) {
    # check for 'site' in file name, but make sure it's only ths last
    point_files <- files[grepl("site", files_short)] 
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_points <- map_dfr(.x = point_files, 
                          .f = function(.x) {
                            file_name = last(str_split(.x, "/")[[1]])
                            df <- read_csv(.x) 
                            # grab all column names except system:index
                            df_names <- colnames(df)[2:length(colnames(df))]
                            # and coerce them to character for joining later
                            df %>% 
                              mutate(across(all_of(df_names),
                                            ~ as.character(.)))%>% 
                              mutate(source = file_name)
                          }) 
    write_feather(all_points, file.path(parent_path, 
                                        "mid",
                                        paste0(file_prefix, "_collated_points_",
                                               version_identifier, ".feather")))
  }
  
  # if centers data are present, subset those, collate, and save
  if (any(grepl("center", files))) {
    center_files <- files[grepl("center", files_short)]
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_centers <- map_dfr(.x = center_files, 
                           .f = function(.x) {
                             file_name = last(str_split(.x, "/")[[1]])
                             df <- read_csv(.x) 
                             # grab all column names except system:index
                             df_names <- colnames(df)[2:length(colnames(df))]
                             # and coerce them to character for joining later
                             df %>% 
                               mutate(across(all_of(df_names),
                                             ~ as.character(.)))%>% 
                               mutate(source = file_name)
                           }) 
    write_feather(all_centers, file.path(parent_path, 
                                         "mid",
                                         paste0(file_prefix, "_collated_centers_",
                                                version_identifier, ".feather")))
  }
  
  #if polygon data are present, subset those, collate, and save
  if (any(grepl("polygon", files))) {
    poly_files <- files[grepl("polygon", files_short)]
    # collate files, but add the filename, since this *could be* is DSWE 1 + 3
    all_polys <- map_dfr(.x = poly_files,
                         .f = function(.x) {
                           file_name = last(str_split(.x, "/")[[1]])
                           df <- read_csv(.x) 
                           # grab all column names except system:index
                           df_names <- colnames(df)[2:length(colnames(df))]
                           # and coerce them to numeric for joining later
                           df %>% 
                             mutate(across(all_of(df_names),
                                           ~ as.numeric(.)))%>% 
                             mutate(source = file_name)
                         })
    
    write_feather(all_polys, file.path(parent_path, 
                                       "mid",
                                       paste0(file_prefix, "_collated_polygons_",
                                              version_identifier, ".feather")))
  }
  
  # return the list of files from this process
  list.files(file.path(parent_path, "mid"),
             pattern = file_prefix,
             full.names = TRUE) %>% 
    #but make sure they are the specified version
    .[grepl(version_identifier, .)]
}