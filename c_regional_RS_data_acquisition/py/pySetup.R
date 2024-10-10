
library(reticulate)

# NOTE, IF YOU ALTER THIS SCRIPT, YOU WILL NEED TO DELETE THE 'ENV' FOLDER
# SO THAT CHANGES ARE REBUILT IN NEW VENV

# activate conda env or create conda env and modules for the venv
tryCatch(use_condaenv(file.path(getwd(), "env")),
         warning = function(w){
           print("conda environment activated")
         },
         error = function(e) {
           # install miniconda if necessary
           try(install_miniconda())
           #create a conda environment named "mod_env" with the packages you need
           conda_create(envname = file.path(getwd(), "env"))
           conda_install(envname = "env/", 
                         packages = c("earthengine-api", "pandas", "fiona", "pyreadr"))
           # set the new python environment
           use_condaenv(file.path(getwd(), "env/"))
           print("conda environment created and activated")
         }
)
