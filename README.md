# hurricane-deploy
The deployment repository for a hurricane forecasting system based on machine
learning and deep learning methods

# Quickstart

  - A **authentication.json** is required for authentication of cloud storage to download the artificial intelligence Tensorflow models.
  - A **credentials.csv** is required for authentication of the SMTP server to send emails.

1. Navigate to the `docker` directory in this repository
2. Run the docker command, `sudo docker build --no-cache -t hurricane .` to install the deployment using docker
3. Run the docker command, `sudo docker run -d hurricane` to activate software that will run email reports every hour

Note that the virtualized deployment utilizes the cron script, `0 * * * * python /hurricane-deploy/report.py >> /var/log/cron.log 2>&1`, to generate reports.

## Import most recent Atlantic tropical storms

From this NHC resource described here, , we can import the most recent tropical
storms using the following code.

```python
import update.py
results = update.nhc()
```

This returns an object of the following form,

    array of dict
        Each dictionary is in the following form,
        {
            "storm" : string # the storm ID from the NHC
            "metadata" : dict # the kml files used to create the results
            "entries" : array of dict # The data for the storm in the form,
                {
                    'time' : Datetime,
                    'wind' : Knots,
                    'lat' : Decimal Degrees,
                    'lon' : Decimal Degrees,
                    'pressure' : Barometric pressure (mb)
                }
        }
