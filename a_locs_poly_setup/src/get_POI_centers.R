#' @title Calculate POI centers
#' 
#' @description
#' Function to calculate the point of inaccessibility (equivalent of Chebyshev 
#' center) for a {sf} of polygons
#' 
#' @param polygons NHDPlusHR polygons {sf} object
#' @param out_file character string - filename for the output file
#' @returns filepath for new {sf} file that contains the points calculated using
#' polylabelr::poi() function, where the {sf} crs is EPSG:4326 (WGS84)
#' 
#' 
get_POI_centers <- function(polygons, out_file) {
  
  # create an empty tibble
  poi_df = tibble(
    permanent_identifier = character(),
    Longitude = numeric(),
    Latitude = numeric(),
    dist_m = numeric()
  )
  
  # for each polygon, calculate a center. Because sf doesn't map easily, using a loop.
  for (i in 1:length(polygons[[1]])) {
    poi_df  <- poi_df %>% add_row()
    one_wbd <- polygons[i, ]
    # transform crs, NHD is already in EPSG:4326, but just in case there is an outlier
    one_wbd <- st_transform(one_wbd, crs = "EPSG:4326")
    # get coordinates to calculate UTM zone. This is an adaptation of code from
    # Xiao Yang's code in EE - Yang, Xiao. (2020). Deepest point calculation 
    # for any given polygon using Google Earth Engine JavaScript API 
    # (Version v 1). Zenodo. https://doi.org/10.5281/zenodo.4136755
    coord_for_UTM <- one_wbd %>% st_coordinates()
    mean_x <- mean(coord_for_UTM[,1])
    mean_y <- mean(coord_for_UTM[,2])
    # calculate the UTM zone using the mean value of Longitude for the polygon
    utm_suffix <- as.character(ceiling((mean_x + 180) / 6))
    utm_code <- if_else(mean_y >= 0,
                        # EPSG prefix for N hemisphere
                        paste0('EPSG:326', utm_suffix),
                        # for S hemisphere
                        paste0('EPSG:327', utm_suffix))
    # transform wbd to UTM
    one_wbd_utm <- st_transform(one_wbd, 
                                crs = utm_code)
    # get UTM coordinates
    coord <- one_wbd_utm %>% st_coordinates()
    x <- coord[ ,1]
    y <- coord[ ,2]
    # using coordinates, get the poi distance, here precision is in meters
    poly_poi <- poi(x,y, precision = 1)
    # add info to poi_df
    poi_df$permanent_identifier[i] = polygons[i, ]$permanent_identifier
    poi_df$dist_m[i] = poly_poi$dist
    # make a point feature and re-calculate decimal degrees in WGS84
    point <- st_point(x = c(as.numeric(poly_poi$x),
                            as.numeric(poly_poi$y)))
    point <- st_sfc(point, crs = utm_code)
    point <- st_transform(point, crs = 'EPSG:4326')
    
    new_coords <- point %>% st_coordinates()
    poi_df$Longitude[i] = new_coords[ ,1]
    poi_df$Latitude[i] = new_coords[ ,2]
  }
  poi_df <- poi_df %>% 
    distinct()
  poly_poi <- polygons %>%
    st_drop_geometry() %>% 
    left_join(., poi_df) %>% 
    mutate(location_type = "poi_center")
  poi_geo <- st_as_sf(poly_poi, coords = c("Longitude", "Latitude"), crs = st_crs(polygons)) %>% 
    st_transform(., "EPSG:4326") 
  write_sf(poi_geo, file.path("a_locs_poly_setup/out", paste0(out_file,".gpkg")))
  # return poi sf
  poi_geo
}
