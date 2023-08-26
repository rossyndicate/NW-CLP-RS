#' Function to create summary figures for each band from a specific corrected
#' dataset
#' 
#' @param corrected_file filepath of a collated, corrected data file
#' @returns silently saves a number of jpg files showing the raw Rrs, corrected
#' to LS7, and corrected to LS8
#' 
#' 
make_Rrs_correction_figures <- function(corrected_file) {
  # ggsave will create folder paths
  # load file and get helpful info from filename
  data <- read_feather(corrected_file)
  #get some info for saving the file
  filename <- str_split(corrected_file, "/")[[1]][4]
  file_prefix <- str_split(filename, "_")[[1]][1]
  file_suffix <- str_split(filename, "_v")[[1]][2]
  DSWE <- if_else(grepl("DSWE1", corrected_file), "DSWE1", "DSWE3")
  type <- case_when(grepl("point", corrected_file) ~ "point",
                    grepl("poly", corrected_file) ~ "poly",
                    grepl("center", corrected_file) ~ "center")
  # load band names 
  band_names <- tar_read(p2_5_9_band_list)
  # create figs for bands shared between LS5-9
  walk(.x = band_names,
       function(.x) {
         band <- str_split(.x, '_')[[1]][2]
         corr7 <- paste0(.x, '_corr7')
         corr8 <- paste0(.x, '_corr8')
         flag7 <- paste0('flag_', band, '_7')
         flag8 <- paste0('flag_', band, '_8')
         subset <- data %>% 
           select(any_of(names(data)[grepl(band, names(data))]))
         raw <- ggplot(data, aes(x = date, y = !!sym(.x), color = mission)) +
           geom_point(alpha = 0.5) +
           scale_color_viridis_d() +
           theme_bw() +
           labs(x = NULL, 
                y = paste('median', band, 'Rrs\n(raw)'),
                title = paste(file_prefix, band, 'summary')) +
           theme(legend.position = 'bottom', 
                 legend.box="vertical", 
                 legend.margin=margin()) +
           guides(color=guide_legend(nrow=2,byrow=TRUE)) +
           theme(plot.title = element_text(hjust = 0.5, face = 'bold'),
                 plot.subtitle = element_text(hjust = 0.5)) 
         corrected_7 <- ggplot(data, aes(x = date, y = !!sym(corr7), 
                                         color = mission, shape = !!sym(flag7))) +
           geom_point(alpha = 0.5) +
           scale_color_viridis_d() +
           theme_bw() +
           labs(x = NULL, 
                y = paste('median', band, 'Rrs\n(relative to LS7 Rrs)')) +
           theme(legend.position = 'bottom', 
                 legend.box="vertical", 
                 legend.margin=margin()) +
           guides(color=guide_legend(nrow=2,byrow=TRUE)) +
           theme(plot.title = element_text(hjust = 0.5, face = 'bold'),
                 plot.subtitle = element_text(hjust = 0.5)) 
         corrected_8 <- ggplot(data, aes(x = date, y = !!sym(corr8), 
                                         color = mission, shape = !!sym(flag8))) +
           geom_point(alpha = 0.5) +
           scale_color_viridis_d() +
           theme_bw() +
           labs(x = NULL, 
                y = paste('median', band, 'Rrs\n(relative to LS8 Rrs)')) +
           theme(legend.position = 'bottom', 
                 legend.box="vertical", 
                 legend.margin=margin()) +
           guides(color=guide_legend(nrow=2,byrow=TRUE)) +
           theme(plot.title = element_text(hjust = 0.5, face = 'bold'),
                 plot.subtitle = element_text(hjust = 0.5)) 
         for_out_of_range <- ggplot(data, aes(x = date, y = !!sym(corr8),
                                              shape = !!sym(flag8))) +
           geom_point() +
           theme_bw() +
           theme(legend.position = 'bottom') +
           scale_shape(name = 'correction flag')
         plot_grid(raw + theme(legend.position = 'none'), 
                   corrected_7 + theme(legend.position = 'none'), 
                   corrected_8 + theme(legend.position = 'none'),
                   get_legend(for_out_of_range),
                   get_legend(raw), 
                   nrow = 5,
                   rel_heights = c(1.1, 1, 1, 0.2, 0.2))
         ggsave(file.path('3_apply_handoff_coefficients/figs/',
                          file_prefix,
                          type,
                          paste0(band, '_correction_summary.jpg')),
                last_plot(),
                height = 8,
                width = 6,
                units = 'in',
                dpi = 200)
       })
  # and now for the Aerosol band (just raw and relative to LS8)
  subset <- data %>% 
    select(any_of(names(data)[grepl('Aerosol', names(data))]))
  raw <- ggplot(data, aes(x = date, y = med_Aerosol, color = mission)) +
    geom_point(alpha = 0.5) +
    scale_color_viridis_d() +
    theme_bw() +
    labs(x = NULL, 
         y = paste('median Aerosol Rrs\n(raw)'),
         title = paste(file_prefix, 'Aerosol summary')) +
    theme(legend.position = 'bottom', 
          legend.box="vertical", 
          legend.margin=margin()) +
    guides(color=guide_legend(nrow=2,byrow=TRUE)) +
    theme(plot.title = element_text(hjust = 0.5, face = 'bold'),
          plot.subtitle = element_text(hjust = 0.5)) 
  corrected_8 <- ggplot(data, aes(x = date, y = med_Aerosol_corr8, 
                                  color = mission, shape = flag_Aerosol_8)) +
    geom_point(alpha = 0.5) +
    scale_color_viridis_d() +
    theme_bw() +
    labs(x = NULL, 
         y = paste('median', 'Aersolol Rrs\n(relative to LS8 Rrs)')) +
    theme(legend.position = 'bottom', 
          legend.box="vertical", 
          legend.margin=margin()) +
    guides(color=guide_legend(nrow=2,byrow=TRUE)) +
    theme(plot.title = element_text(hjust = 0.5, face = 'bold'),
          plot.subtitle = element_text(hjust = 0.5)) 
  for_out_of_range <- ggplot(data, aes(x = date, y = med_Aerosol_corr8,
                                       shape = flag_Aerosol_8)) +
    geom_point() +
    theme_bw() +
    theme(legend.position = 'bottom') +
    scale_shape(name = 'correction flag')
  plot_grid(raw + theme(legend.position = 'none'), 
            corrected_8 + theme(legend.position = 'none'),
            get_legend(for_out_of_range),
            get_legend(raw), 
            nrow = 4,
            rel_heights = c(1.6, 1.5, 0.2, 0.2))
  ggsave(file.path('3_apply_handoff_coefficients/figs/',
                   file_prefix,
                   type,
                   'Aerosol_correction_summary.jpg'),
         last_plot(),
         height = 8,
         width = 6,
         units = 'in',
         dpi = 200)
}