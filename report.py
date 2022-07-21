import pandas as pd
import logging
import predict
import update
import smtplib
import datetime
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# Setup logs
logging.basicConfig(filename='report.log', level=logging.DEBUG)

# Replace sender@example.com with your "From" address.
# This address must be verified.
SENDER = 'husmani@fluids.ai'
SENDERNAME = 'Hurricane AI'

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
RECIPIENT  = 'hammadus@gmail.com,hurricaneaiml@gmail.com'

# SMTP Credentials
credentials_df = pd.read_csv('/root/credentials.csv')
credentials = credentials_df.iloc[0]
USERNAME_SMTP = credentials['smtp_user']
PASSWORD_SMTP = credentials['smtp_pass']

# (Optional) the name of a configuration set to use for this message.
# If you comment out this line, you also need to remove or comment out
# the "X-SES-CONFIGURATION-SET:" header below.
# CONFIGURATION_SET = "ConfigSet"

HOST = credentials['host']
PORT = int(credentials['port'])

# The subject line of the email.
SUBJECT = 'HURAIM Hourly Reports'

# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("HURAIM Hourly Reports\r\n"
             "This email has an attached HTML document. Please reply "
             "for troubleshooting."
            )

# The HTML body of the email.
data = update.nhc()
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Hurricane Artificial Intelligence using Machine Learning Hourly Reports</h1><br>
  This experimental academic weather report was generated using the software available at https://github.com/hammad93/hurricane-deploy <br>
  <h2>Atlantic Tropical Storms and Hurricanes</h2>"""
for storm in data :
    # get the prediction for this storm
    try :
      prediction = predict.predict_universal([storm])[0]
      print(prediction)
    except Exception as error :
      prediction = {
        'error' : error
      }
    
    # add to HTML
    html = f"""
    <h2>{storm['id']} ({storm['name']})</h2>
    """

    # storm metadata
    html += f"""<h3>
    As of {str(storm['entries'][-1]['time'])}<br>
    Wind : {round(1.150779 * storm['entries'][-1]['wind'])} mph, {storm['entries'][-1]['wind']} Knots<br>
    Pressure : {storm['entries'][-1]['pressure']} mb<br>
    Location : (lat, lon) ({storm['entries'][-1]['lat']}, {storm['entries'][-1]['lon']}<br>)
    </h3>"""

    # print the informative error
    if 'error' in prediction.keys() :
      html += f"""
      <h3><p style="color:red">Errors in running forecast,</p></h3>
      <pre>
       {prediction['error']}
      </pre>
        """

    else :
        # put the predictions
        html += """
          <table>
            <tr>
              <th><b>Time</b></th>
              <th><b>Wind (mph)</b></th>
              <th><b>Coordinates (Decimal Degrees)</b></th>
            <tr>
        """
        for value in prediction :
            # datetime object keys are predictions
            if isinstance(value, datetime.datetime) :
                html += f"""
            <tr>
              <th>{value.isoformat()}</th>
              <th>{prediction[value]['max_wind(mph)']:.2f}</th>
              <th>{prediction[value]['lat']:.2f}, {prediction[value]['lon']:.2f}</th>
            <tr>            
                """
        html += "</table>"
    BODY_HTML += html
BODY_HTML += """
</body>
</html>
            """

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = SUBJECT
msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
msg['To'] = RECIPIENT
# Comment or delete the next line if you are not using a configuration set
# msg.add_header('X-SES-CONFIGURATION-SET',CONFIGURATION_SET)

# Record the MIME types of both parts - text/plain and text/html.
part1 = MIMEText(BODY_TEXT, 'plain')
part2 = MIMEText(BODY_HTML, 'html')

# Attach parts into message container.
# According to RFC 2046, the last part of a multipart message, in this case
# the HTML message, is best and preferred.
msg.attach(part1)
msg.attach(part2)

# Try to send the message.
try:
    server = smtplib.SMTP(HOST, PORT)
    server.ehlo()
    server.starttls()
    #stmplib docs recommend calling ehlo() before & after starttls()
    server.ehlo()
    server.login(USERNAME_SMTP, PASSWORD_SMTP)
    server.sendmail(SENDER, RECIPIENT, msg.as_string())
    server.close()
# Display an error message if something goes wrong.
except Exception as e:
    print ("Error: ", e)
else:
    print ("Email sent!")
