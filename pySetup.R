
library(reticulate)

# NOTE, IF YOU ALTER THIS SCRIPT, YOU WILL NEED TO DELETE THE "ENV" FOLDER
# SO THAT CHANGES ARE REBUILT IN NEW VENV

# activate conda env or create conda env and modules for the venv
tryCatch({
  use_condaenv(file.path(getwd(), "env/"))
  print("conda environment activated")
},
warning = function(w) {
  # if the warning is expected, go on with life
  if (!grepl("failed to initialize requested version of Python", conditionMessage(w))) {
    message("conda environment activated")
  } else {
    message(conditionMessage(w))
    stop("There was an error initializing Python. Restart your R session and try running the pipeline again.")
  }
},
error = function(e) {
  # if the error is "Unable to locate conda environment"
  if (grepl("Unable to locate conda environment", conditionMessage(e))) {
    # install miniconda if necessary
    try(install_miniconda())
    # create a conda environment named "mod_env" with the packages you need
    conda_create(envname = file.path(getwd(), "env/"), 
                 python_version = "3.10.13")
    conda_install(envname = file.path(getwd(), "env/"),
                  python_version = "3.10.13",  
                  packages = c("earthengine-api==1.4.0", 
                               "pandas==2.0.3", 
                               "pyreadr==0.5.2", 
                               "pyyaml==6.0.2",
                               "numpy==1.24.4"))
    # set the new python environment
    use_condaenv(file.path(getwd(), "env/"))
    print("conda environment created and activated")
  } else if (grepl("Please restart the R session if you need to attach reticulate to a different version of Python.", conditionMessage(e))) {
    stop("There was an error initializing Python. Restart your R session and try running the pipeline again.")
  }
},
finally = function(f) {
  # install miniconda if necessary
  try(install_miniconda())
  # create a conda environment named "mod_env" with the packages you need
  conda_create(envname = file.path(getwd(), "env/"), 
               python_version = "3.10.13")
  conda_install(envname = file.path(getwd(), "env/"),
                python_version = "3.10.13",  
                packages = c("earthengine-api==1.4.0", 
                             "pandas==2.0.3", 
                             "pyreadr==0.5.2", 
                             "pyyaml==6.0.2",
                             "numpy==1.24.4"))
  # set the new python environment
  use_condaenv(file.path(getwd(), "env/"))
  print("conda environment created and activated")
})
