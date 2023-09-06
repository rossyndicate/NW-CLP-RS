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
#' @returns filepath for new .gpkg file that contains the combined {sf} objects 
#' and data_group parameter
#' 
#' 
combine_and_simplify_sfs <- function(sf_1, data_group_1, sf_2, data_group_2, filename) {
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
  collated_sf <- bind_rows(sf_1, sf_2) 
  dupes <- collated_sf %>% 
    st_drop_geometry() %>% 
    group_by(Permanent_Identifier) %>% 
    summarize(n = n()) %>% 
    filter(n > 1) %>% 
    ungroup()
  dupe_id = unique(dupes$Permanent_Identifier)
  lighter_coll_sf <- collated_sf %>% 
    st_drop_geometry() %>% 
    filter(!Permanent_Identifier %in% dupe_id)
  condensed_sf <- collated_sf %>%
    st_drop_geometry() %>% 
    filter(Permanent_Identifier %in% dupe_id) %>% 
    select(Permanent_Identifier, data_group) %>%  
    group_by(Permanent_Identifier) %>% 
    summarize(data_group = toString(unique(data_group))) %>% 
    left_join(., collated_sf %>% st_drop_geometry() %>% select(-data_group)) %>% 
    distinct()
  collated_simplified_sf <- full_join(lighter_coll_sf, condensed_sf) %>% 
    left_join(., tibble(collated_sf) %>% select(-data_group)) %>% 
    st_as_sf() %>% 
    distinct()
  st_write(collated_simplified_sf, paste0('0_locs_poly_setup/out/', filename, '.gpkg'), append = F)
  paste0('0_locs_poly_setup/out/', filename, '.gpkg')
}