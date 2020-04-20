import argparse
import email
import os
import re
import shutil
import smtplib
import ssl
import sys

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

def validate_email(email_address):
    """Valides an email address"""
    regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if re.search(regex, email_address):
        return True
    return False

def validate_email_list(email_list):
    """Validates each email_address in the list"""
    for email_address in email_list:
        valid = validate_email(email_address)
        if not valid:
            email_list.remove(email_address)
            error = f"The email for {email_addresss} does not appear to be valid."
            # TODO: Log the email_address that was flagg as not valid
            print(error)
    return email_list

def get_email_list(pdf_directory):
    """returns a list of email address' """
    email_list = []
    directory = Path.cwd() / pdf_directory
    if not directory.exists():
        error = "The specified directory does not exist."
        print(error)
        sys.exit()
    for document in directory.iterdir():
        if document.is_file() and document.suffix == '.pdf':
            email_address = document.stem
            email_list.append(email_address)
    return email_list

def get_emails_and_pdfs(email_list, pdf_directory):
    """ Returns a list of tuples containg: (email, pdf-path)"""
    # Create a directory to store all valid_pdfs
    valid_pdf_data = []
    pdf_directory_path = Path.cwd() / pdf_directory
    valid_pdf_directory = Path.cwd() / pdf_directory / 'valid_pdfs'
    try:
        valid_pdf_directory.mkdir()
    except FileExistsError:
        # Empty the directory
        for document in valid_pdf_directory.iterdir():
            try:
                document.unlink()
            except OSError as error:
                error = f"There was an error deleting {document} it was: {error}"
                #TODO: log this error
                print(error)
    for email in email_list:
        username = email.split("@")[0]
        current_filename = email+".pdf"
        current_file_location = str(pdf_directory_path / current_filename)
        new_filename = "Something_" + username + ".pdf"
        new_file_location = valid_pdf_directory / new_filename
        try:
            shutil.copy2(current_file_location, new_file_location)
        except SameFileError as e:
            error = f"""
                There was a SameFileError trying to copy2 with {current_file_location} and 
                {new_file_location}. See error: {e}
            """
            print(error)
            #TODO: log this error
        except OSError as e:
            error = f"""
                There was an OSError most likely caused by an unwritable destination!
                See error: {e}
            """
            print(error)
            #TODO: log this error
        email_data = (email, new_filename, new_file_location)
        valid_pdf_data.append(email_data)
    return valid_pdf_data


def send_emails(pdf_data):
    for email, pdf_name, pdf_location in pdf_data:
        subject = "Test Subject"
        body = "Some Dummy Body Text"
        sender_email = os.environ.get('SENDER_EMAIL')
        reciever_email = email
        password = os.environ.get('SMTP_PASSWORD')
        smtp_address = os.environ.get('SMTP_ADDRESS')
        smtp_port = os.environ.get('SMTP_PORT')


        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = reciever_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        with open(pdf_location, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {pdf_name}",
        )

        message.attach(part)
        text = message.as_string()

        # Login and send
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_address, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.sendmail(sender_email, reciever_email, text)
        #TODO: log that we succesfully send the email or catch an error
    return True

if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(description="This will send emails!")
    PARSER.add_argument(
        "-d",
        "--dir",
        required=True,
        help="""
            The directory which contains the PDFs (must be relative to this script)
        """
        )
    PARSER.add_argument(
        "-t",
        "--test",
        required=False,
        help="""
            Dry run of the script which tells you if the script will work as expected.
        """
        )
    ARGS = PARSER.parse_args()
    pdf_directory = ARGS.dir
    is_test = ARGS.test 
    email_address_list = get_email_list(pdf_directory)
    valid_email_list = validate_email_list(email_address_list)
    # Order the list and get rid of duplicates
    sorted_valid_emails = list(sorted(set(valid_email_list)))
    email_pdf_tuples = get_emails_and_pdfs(sorted_valid_emails, pdf_directory)
    sent = send_emails(email_pdf_tuples)
    if sent:
        print("All done!")

