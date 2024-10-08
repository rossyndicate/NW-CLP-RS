#' @title Read and format yaml file
#' 
#' @description 
#' Function to read in yaml, reformat and pivot for easy use in scripts
#' 
#' @param yml_file user-specified file containing configuration details for the
#' pull.
#' @returns filepath for the .csv of the reformatted yaml file. Silently saves 
#' the .csv in the `data_acquisition/in` directory path.
#' 
#' 
format_yaml <-  function(yml_file) {
  yaml <-  read_yaml(yml_file)
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
  write_csv(unnested, "data_acquisition/in/yml.csv")
  "data_acquisition/in/yml.csv"
}

