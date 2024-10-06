import os
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from fastapi import FastAPI
from smtplib import SMTP_SSL

from services import IMAP4_Client

app = FastAPI()

############### -- TEST -- ########################
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

smtp_server = 'smtp.gmail.com'
smtp_port = 587
username = 'tu_email@gmail.com'
password = 'tu_contraseña'
###################################################


@app.get("/email")
def get_emails(mailbox: str = None, criteria: str = "ALL", batch_size: int = 10):

    with IMAP4_Client(IMAP_SERVER) as client:
        client.connect(USERNAME, PASSWORD)
        client.select_mailbox(mailbox)

        # Search emails UID's based on the criteria
        emails_uids: list[bytes] = client.search_emails(criteria)

        # Proccess emails by batchs
        emails: list = []
        for index in range(0, len(emails_uids), batch_size):
            batch_uids: list[bytes] = emails_uids[index:index + batch_size]
            uids_str: str = ','.join(map(lambda x: x.decode(), batch_uids))

            # Get emails
            batch_emails: list[EmailMessage] = client.fetch_emails(uids_str)
            emails.extend(batch_emails)

    return {"emails": emails}


@app.get("/email/mailboxes")
def get_mailboxes(directory: str = '""', pattern: str = "*"):

    with IMAP4_Client(IMAP_SERVER) as client:
        client.connect(USERNAME, PASSWORD)
        mailboxes = client.list_mailboxes(directory.encode(), pattern.encode())

    return {"mailboxes": mailboxes}


@app.post("/email/send")
def send(sender: str, receiver: str, subject: str, body: str):
    message = MIMEMultipart()

    message['From'] = sender
    message['To'] = receiver
    message['Subject'] = subject

    message.attach(MIMEText(body, 'plain'))

    try:
        with SMTP_SSL(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)

            text = message.as_string()

            server.sendmail(sender, receiver, text)
    except Exception as e:
        raise RuntimeError(f"Error sending email: {e}")
