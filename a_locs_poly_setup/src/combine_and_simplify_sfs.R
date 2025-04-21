#' @title Combine {sf} objects
#' 
#' @description
#' Function to combine two {sf} objects and define data groups
#' 
#' @param sf_1 a {sf} object 
#' @param sf_2 a {sf} object 
#' @param data_group_1 text string for data group to be added to the {sf} object (sf_1)
#' can also be NA_character_ if the {sf} object already contains a data_group parameter
#' @param data_group_2 text string for data group to be added to the {sf} object (sf_2)
#' can also be NA_character_ if the {sf} object already contains a data_group parameter
#' @param filename a text string that will become the filename of the output .gpkg
#' @param simplify boolean indicating whether or not simplification by NHD ID is necessary
#' 
#' @returns filepath for new .gpkg file that contains the combined {sf} objects 
#' and data_group parameter
#' 
#' 
combine_and_simplify_sfs <- function(sf_1, data_group_1, sf_2, data_group_2, filename, simplify) {
  # add data group info if necessary
  if (!is.na(data_group_1)) {
    sf_1 <- sf_1 %>% 
      mutate(data_group = data_group_1)
  }
  if (!is.na(data_group_2)) {
  sf_2 <- sf_2 %>% 
    mutate(data_group = data_group_2)
  }
  # if the crs is not the same, transform
  if(st_crs(sf_1) != st_crs(sf_2)){
    crs = st_crs(sf_1)
    sf_2 <- st_transform(sf_2, crs)
  }
  # join the two sf objects
  collated_sf <- bind_rows(sf_1, sf_2) 
  # if simplification necessary then collate by permanent id
  if(simplify == TRUE) {
    dupes <- collated_sf %>% 
      st_drop_geometry() %>% 
      group_by(permanent_identifier) %>% 
      summarize(n = n()) %>% 
      filter(n > 1) %>% 
      ungroup()
    dupe_id <- unique(dupes$permanent_identifier)
    lighter_coll_sf <- collated_sf %>% 
      st_drop_geometry() %>% 
      filter(!permanent_identifier %in% dupe_id)
    condensed_sf <- collated_sf %>%
      st_drop_geometry() %>% 
      filter(permanent_identifier %in% dupe_id) %>% 
      select(permanent_identifier, data_group) %>%  
      group_by(permanent_identifier) %>% 
      summarize(data_group = toString(unique(data_group))) %>% 
      left_join(., collated_sf %>% st_drop_geometry() %>% select(-data_group)) %>% 
      distinct()
    collated_simplified_sf <- full_join(lighter_coll_sf, condensed_sf) %>% 
      left_join(., tibble(collated_sf) %>% select(-data_group)) %>% 
      st_as_sf() %>% 
      distinct()
    st_write(collated_simplified_sf, paste0("a_locs_poly_setup/out/", filename, ".gpkg"), append = F)
    return(collated_simplified_sf)
  } else {
    st_write(collated_sf, paste0("a_locs_poly_setup/out/", filename, ".gpkg"), append = F)
    return(collated_sf)
  }
}