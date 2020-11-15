import pandas as pd
import logging
import predict
import update
import smtplib
import datetime
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Setup logs
logging.basicConfig(filename='report.log', level=logging.DEBUG)

# Gather credentials
credentials = pd.read_csv('/root/credentials.csv')
print(credentials)
logging.warning('Read in credentials for SMTP server')

# Replace sender@example.com with your "From" address.
# This address must be verified.
SENDER = 'husmani@fluids.ai'
SENDERNAME = 'Hurricane AI'

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
RECIPIENT  = 'hammadus@gmail.com'

# Replace smtp_username with your Amazon SES SMTP user name.
USERNAME_SMTP = credentials.iloc[0,1]

# Replace smtp_password with your Amazon SES SMTP password.
PASSWORD_SMTP = credentials.iloc[0,2]

# (Optional) the name of a configuration set to use for this message.
# If you comment out this line, you also need to remove or comment out
# the "X-SES-CONFIGURATION-SET:" header below.
# CONFIGURATION_SET = "ConfigSet"

# If you're using Amazon SES in an AWS Region other than US West (Oregon),
# replace email-smtp.us-west-2.amazonaws.com with the Amazon SES SMTP
# endpoint in the appropriate region.
HOST = "email-smtp.us-west-2.amazonaws.com"
PORT = 587

# The subject line of the email.
SUBJECT = 'Amazon SES Test (Python smtplib)'

# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("Amazon SES Test\r\n"
             "This email was sent through the Amazon SES SMTP "
             "Interface using the Python smtplib package."
            )

# The HTML body of the email.
data = update.nhc()
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Universal Output</h1>"""
for storm in data :
    # get the prediction for this storm
    prediction = predict.predict_universal([storm])[0]

    # add to HTML
    html = f"""
    <h2>{storm['storm']}({storm['metadata']['ExtendedData']['tc:name']})</h2>
    """
    # print the informative error
    if 'error' in prediction.keys() :
        html += f"""
      <pre>
       {prediction['error']}
      </pre
        """
        continue

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
          <th><b>{value.isoformat()}</b></th>
          <th><b>{value['max_wind(mph)']:.2f}</b></th>
          <th><b>{value['lat']:.2f}, {value['lon']:.2f}</b></th>
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
