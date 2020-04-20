import logging

from logging import FileHandler
from logging import Formatter
from pathlib import Path


LOG_FORMAT = "%(asctime)s - [%(levelname)s]: %(message)s - in %(pathname)s: %(lineno)d"
LOG_LEVEL = logging.INFO

LOG_DIR = Path.cwd() / 'logs'
if not LOG_DIR.is_dir():
    LOG_DIR.mkdir()

ERRORS_NAME = 'errors.log'
ERROR_LOG_FILE = Path.cwd() / 'logs' / ERRORS_NAME


INVALID_EMAILS_NAME = 'invalid_emails.log'
INVALID_EMAIL_FILE = Path.cwd() / 'logs' / INVALID_EMAILS_NAME


SENT_EMAILS_NAME = 'sent_emails.log'
SENT_EMAIL_FILE = Path.cwd() / 'logs' / SENT_EMAILS_NAME


# ERROR LOG
error_log = logging.getLogger('error_log')
error_log.setLevel(LOG_LEVEL)
error_log_file_handler = FileHandler(ERROR_LOG_FILE)
error_log_file_handler.setLevel(LOG_LEVEL)
error_log_file_handler.setFormatter(Formatter(LOG_FORMAT))
error_log.addHandler(error_log_file_handler)

# INVALID EMAIL LOG
invalid_email_log = logging.getLogger('invalid_email_log')
invalid_email_log.setLevel(LOG_LEVEL)
invalid_email_log_file_handler = FileHandler(INVALID_EMAIL_FILE)
invalid_email_log_file_handler.setLevel(LOG_LEVEL)
invalid_email_log_file_handler.setFormatter(Formatter(LOG_FORMAT))
invalid_email_log.addHandler(invalid_email_log_file_handler)

# SENT EMAIL LOG
sent_email_log = logging.getLogger('sent_email_log')
sent_email_log.setLevel(LOG_LEVEL)
sent_email_file_handler = FileHandler(SENT_EMAIL_FILE)
sent_email_file_handler.setLevel(LOG_LEVEL)
sent_email_file_handler.setFormatter(Formatter(LOG_FORMAT))
sent_email_log.addHandler(sent_email_file_handler)
