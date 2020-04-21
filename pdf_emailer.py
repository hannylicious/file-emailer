import argparse
import email
import logging
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
from loggers import error_log
from loggers import invalid_email_log
from loggers import sent_email_log
from pathlib import Path

import pyodbc
import requests

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
            error = f"The email for {email_address} does not appear to be valid."
            invalid_email_log.info(error)
            continue
    return email_list

def generate_documents(pdf_directory, employee_id, employee_email):
    url = os.environ.get("PDF_EMAILER_DOC_ENDPOINT")
    endpoint = url + str(employee_id)
    directory = Path.cwd() / pdf_directory
    try:
        directory.mkdir()
    except FileExistsError:
        pass
    response = requests.get(endpoint)
    if response.status_code == 200:
        filename = str(directory) + "/" + employee_email + ".pdf"
        with open(filename, 'wb') as f:
                f.write(response.content)
                f.close()

def run_stored_procedure(stored_procedure, pdf_directory):
    server = os.environ.get("PDF_EMAILER_HOST")
    database = os.environ.get("PDF_EMAILER_DATABASE")
    port = os.environ.get("PDF_EMAILER_PORT")
    db_username = os.environ.get("PDF_EMAILER_USER")
    db_password = os.environ.get("PDF_EMAILER_PASSWORD")
    driver = os.environ.get("ODBC_DRIVER")
    try:
        connection = pyodbc.connect(
            'DRIVER='
            + driver
            + ";SERVER="
            + server
            + ";PORT="
            + port
            + ";DATABASE="
            + database
            + ";UID="
            + db_username
            + ";PWD="
            + db_password
        )
        cursor = connection.cursor()
    except Exception as e:
        print(f"There was an issue with connecting to MSSQL! ERROR: {e}")
        sys.exit()
    try:        
        cursor.execute("{CALL " + stored_procedure + "}")
    except Exception as e:
        print(f"There was an issue executing the stored procedure! ERROR: {e}")
        sys.exit()
    rows = cursor.fetchall()
    for row in rows:
        employee_email = row[0]
        employee_id = row[1]
        generate_documents(pdf_directory, employee_id, employee_email)
    connection.close()

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
    valid_pdf_data = []
    pdf_directory_path = Path.cwd() / pdf_directory
    valid_pdf_directory = Path.cwd() / pdf_directory / 'valid_pdfs'
    try:
        valid_pdf_directory.mkdir()
    except FileExistsError:
        for document in valid_pdf_directory.iterdir():
            try:
                document.unlink()
            except OSError as error:
                error = f"There was an error deleting {document} it was: {error}"
                error_log.error(error)
                sys.exit()
    for email in email_list:
        # TODO: Cleanup username (check that its all good)
        username = email.split("@")[0]
        current_filename = email+".pdf"
        current_file_location = str(pdf_directory_path / current_filename)
        new_filename = "AreYouReturning_" + username + ".pdf"
        new_file_location = valid_pdf_directory / new_filename
        try:
            shutil.copy2(current_file_location, new_file_location)
        except SameFileError as e:
            error = f"""
                There was a SameFileError trying to copy2 with {current_file_location} and 
                {new_file_location}. See error: {e}
            """
            error_log.warning(error)
            pass
        except OSError as e:
            error = f"""
                There was an OSError most likely caused by an unwritable destination!
                Current file location: {current_file_location}
                New file location: {new_file_location}
                See error: {e}
            """
            error_log.error(error)
            sys.exit()
        email_data = (email, new_filename, new_file_location)
        valid_pdf_data.append(email_data)
    return valid_pdf_data

def send_emails(pdf_data, test_run=False):
    context = ssl.create_default_context()
    sender_email = os.environ.get('SENDER_EMAIL')
    password = os.environ.get('SMTP_PASSWORD')
    smtp_address = os.environ.get('SMTP_ADDRESS')
    smtp_port = os.environ.get('SMTP_PORT')
    with smtplib.SMTP_SSL(smtp_address, smtp_port) as server:
        try:
            server.login(sender_email, password)
        except SMTPHeloError as error:
            error_message = (f"""
                There was a HELO error when logging in to SMTP. 
                Error: {error}
            """)
            error_log.error(error_message)
            print(error_message)
            sys.exit()
        except SMTPAuthenticationError as error:
            error_message = (f"""
                There was an AuthenticationError when logging in to SMTP. 
                Error: {error}
            """)
            error_log.error(error_message)
            print(error_message)
            sys.exit()
        except SMTPNotSupportedError as error:
            error_message = (f"""
                There was an SMTPNotSupportedError when logging in to SMTP. 
                Error: {error}
            """)
            error_log.error(error_message)
            print(error_message)
            sys.exit()
        except SMTPException as error:
            error_message = (f"""
                There was an SMTPException when logging in to SMTP. 
                Error: {error}
            """)
            error_log.error(error_message)
            print(error_message)
            sys.exit()
        for email, pdf_name, pdf_location in pdf_data:
            subject = "Test Subject"
            body = "Some Dummy Body Text"
            reciever_email = email

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

            if test_run:
                sent_email_log.info(f"Test Run - would have sent: {email}, {pdf_name}, {pdf_location}")
            else:
                try:
                    server.sendmail(sender_email, reciever_email, text)
                except SMTPRecipientsRefused as error:
                    error_log.error(f"""
                        The recipients refused the email. 
                        Reciever: {reciever_email}
                        Error: {error}
                    """)
                    continue
                except SMTPHeloError as error:
                    error_log.error(f"""
                        There was a HELO error!
                        Reciever: {reciever_email}
                        Error: {error}
                    """)
                    continue
                except SMTPSenderRefused as error:
                    error_log.error(f"""
                        There was a SenderRefused error!
                        Sender: {sender_email}
                        Reciever: {reciever_email}
                        Error: {error}
                    """)
                    continue
                except SMTPDataError as error:
                    error_log.error(f"""
                        There was a Data error!
                        Reciever: {reciever_email}
                        Error: {error}
                    """)
                    continue
                except SMTPNotSupportedError:
                    error_log.error(f"""
                        There was an SMTPNotSupported error!
                        Reciever: {reciever_email}
                        Error: {error}
                    """)
                    continue
                sent_email_log.info(f"""
                    Sent email to: {reciever_email}
                    With attachment: {pdf_name} at {pdf_location}
                    """)
    return True

if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(description="""
        This utility will send emails to the address derived from the 
        pdf fele name for all pdf files in a given directory. 

        Example: some_email@domain.com.pdf -> sends to some_email@domain.com

    """)
    PARSER.add_argument(
        "-d",
        "--directory",
        required=True,
        help="""
            The directory which contains the PDFs (must be relative to this script)
        """
        )
    PARSER.add_argument(
        "-sp",
        "--stored_procedure",
        required=False,
        help="""
            The name of the stored procedure to be run. Include this if you need to 
            generate the PDFs.
        """
        )
    PARSER.add_argument(
        "-t",
        "--test",
        action='store_true',
        required=False,
        help="""
            Dry run of the script which tells you if the script will work as expected.
        """
        )
    ARGS = PARSER.parse_args()
    pdf_directory = ARGS.directory
    stored_procedure = ARGS.stored_procedure
    is_test = ARGS.test
    if stored_procedure:
        # This will run the stored_procedure and generate the
        # pdfs on the given results
        run_stored_procedure(stored_procedure, pdf_directory)
    # Use the given directory to get a list of email_address
    email_address_list = get_email_list(pdf_directory)
    # Get a list of valid emails from the original list
    valid_email_list = validate_email_list(email_address_list)
    # Order the list and get rid of duplicates
    sorted_valid_emails = list(sorted(set(valid_email_list)))
    # Get a list of tuples containing the email_address and the file location
    email_pdf_tuples = get_emails_and_pdfs(sorted_valid_emails, pdf_directory)
    # Iterate across the list and send the emails
    send_emails = send_emails(email_pdf_tuples, is_test)
    if send_emails:
        print("All done! Please check logs for any errors, invalid_emails and sent_emails!")

