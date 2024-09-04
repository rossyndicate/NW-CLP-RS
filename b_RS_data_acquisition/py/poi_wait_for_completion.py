import ee
from pandas import read_csv
import time

# get configs from yml file
yml = read_csv("data_acquisition/in/yml.csv")
# assign proj
eeproj = yml["ee_proj"][0]
#initialize GEE with proj
ee.Initialize(project = eeproj)

# get a list of the 20 most recently submitted tasks
ts = list(ee.batch.Task.list())[0:20]
# set the counter to zero
n_active = 0
# for each of the tasks, see if any read running or ready, if so, add one 
# to the counter
for task in ts:
   if ("RUNNING" in str(task) or "READY" in str(task)):
       n_active += 1
# loop to track if n_active is greater than zero
while (n_active > 0):
  # if it is, wait 2 minutes
  time.sleep(120)
  # and then repoeat!
  ts = list(ee.batch.Task.list())
  n_active = 0
  for task in ts:
    if ("RUNNING" in str(task) or "READY" in str(task)):
      n_active += 1

print('All tasks completed')
