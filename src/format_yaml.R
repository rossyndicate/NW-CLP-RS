#' @title Read and format yaml file
#' 
#' @description 
#' Function to read in yaml, reformat and pivot for easy use in scripts
#' 
#' @param yaml user-specified configuration file containing details for the
#' pull - in this case, this refers to a target that has read/tracked the yaml 
#' file
#' @param parent_path parent filepath where the RS run is occurring
#' @returns dataframe of unnested yaml file for remote sensing pull. Silently saves 
#' the .csv in the `/run/` directory path if configured 
#' for site acquisition.
#' 
#' 
format_yaml <-  function(yaml, parent_path) {
  # create a nested tibble from the yaml file
  nested <-  map_dfr(names(yaml), 
                     function(x) {
                       tibble(set_name = x,
                              param = yaml[[x]])
                     })
  # create a new column to contain the nested parameter name and unnest the name
  nested$desc <- NA_character_
  unnested <- map_dfr(seq(1:length(nested$param)),
                      function(x) {
                        name <- names(nested$param[[x]])
                        nested$desc[x] <- name
                        nested <- nested %>% 
                          unnest(param) %>% 
                          mutate(param = as.character(param))
                        nested[x,]
                      })
  # re-orient to make it easy to grab necessary info in future functions
  unnested <- unnested %>% 
    select(desc, param) %>% 
    pivot_wider(names_from = desc, 
                values_from = param)
  # save the file for the python run, return unnested
  write_csv(unnested, file.path(parent_path, "run/yml.csv"))
  unnested
}

