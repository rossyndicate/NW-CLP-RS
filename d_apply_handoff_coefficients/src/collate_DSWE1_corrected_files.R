#' @title Collate and save all DSWE1 data with coefficients applied
#' 
#' @description
#' Function to collate the resultant to LS7 and to LS8 DSWE1 corrected files 
#' into a single file per file prefix and GEE extraction type for a specific
#' version identifier
#' 
#' @param version_identifier text string; user-specified string to identify the RS pull these
#' data are associated with
#' @returns silently saves a feather file with band information from both the 
#' LS7 correction and LS8 correction
#' 
#' 
collate_DSWE1_corrected_files <- function(version_identifier) {
  #check for out directory
  dir.create("d_apply_handoff_coefficients/out/")
  # get a list of the DSWE 1 corrected files
  corrected_files <- list.files("d_apply_handoff_coefficients/mid/",
                                full.names = TRUE) %>% 
    .[grepl(version_identifier, .)] %>% 
    .[grepl("DSWE1", .)]
  #get some info for parsing out the data to be joined
  filename <- map_chr(corrected_files, 
                  function(x) {str_split(x, "/")[[1]][4]})
  # break out file prefix
  file_prefix <- map_chr(filename, 
                     function(x) {str_split(x, "_")[[1]][1]}) 
  # and file type so we can merge files of the same type
  file_type <- map_chr(filename,
                      function(x) {str_split(x, "_")[[1]][5]})
  # now join the files together, by the file prefixes, and save the resulting
  # feather file
  walk2(.x = file_prefix, .y = file_type,
       function(.x, .y) {
         file_subset <- filename[grepl(.x, filename)] %>% 
           .[grepl(.y, .)]
         collated <- map(file.path("d_apply_handoff_coefficients/mid/",
                                       file_subset), 
                             read_feather) %>% 
           reduce(full_join)
         flag_cols <- names(collated)[grepl("flag", names(collated))]
         # replace NA with "" for figures
         collated <- collated %>% 
           mutate(across(all_of(flag_cols),
                         ~ replace_na(., "")))
         write_feather(collated,
                       file.path("d_apply_handoff_coefficients/out/",
                                 paste0(.x,
                                        "_",
                                        .y,
                                        "_DSWE1_corrected78_",
                                        version_identifier,
                                        ".feather")))
    
  })
  
}
