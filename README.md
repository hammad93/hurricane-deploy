# hurricane-deploy
The deployment repository for a hurricane forecasting system based on machine
learning and deep learning methods

# API Link
## http://nfc.ai:1337/docs

# Quickstart
  - A **credentials.csv** is required for authentication of the SMTP server to send emails. This is stored in a secret gist.
  - Copy the SSL certificates over to the docker directory

1. Navigate to the `docker` directory in this repository
2. Run the docker command, `sudo docker build --no-cache -t hurricane .` to install the deployment using docker
3. Run the docker command, `sudo docker run -d -p 1337:1337 --network=host hurricane` to activate software that will run email reports every hour

Note that the virtualized deployment utilizes the cron script, `0 * * * * python /hurricane-deploy/report.py >> /var/log/cron.log 2>&1`, to generate reports.

# Tips & Tricks
Make sure there is enough swap space for the RAM. You can check with `free -m`

Useful Docker commands,
- `docker container ls`: Lists the containers that are running
- `docker exec -it [NAME] bash`: Executes a bash terminal on a running container

# Database

Install PostgreSQL
- https://web.archive.org/web/20240924180833/https://ubuntu.com/server/docs/install-and-configure-postgresql

Include this to the /etc/postgresql/*/pg_hba.conf file,

```
# all access to all databases for users with an encrypted pass
host  all  all 0.0.0.0/0 scram-sha-256
```

Create the database,
`sudo -u postgres psql`

```sql
create database hurricane_live;
\c hurricane_live;
```

Create the live storm database,
https://gist.github.com/hammad93/2c9325aec16a03c9d6a9e17778040a07

Create the archive ingest database,
https://gist.github.com/hammad93/c22b484c120f5c605a516647a6b01f6b


## Credentials

The credentials in CSV format need to be in the `docker` directory with a filename `credentials.csv`

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
