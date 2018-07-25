from imbox.imap import ImapTransport
from imbox.parser import parse_email
from imbox.query import build_search_query

import logging
logger = logging.getLogger(__name__)

__version_info__ = (0, 9, 5)
__version__ = '.'.join([str(x) for x in __version_info__])


class Imbox:

    def __init__(self, hostname, username=None, password=None, ssl=True,
                 port=None, ssl_context=None, policy=None, starttls=False):

        self.server = ImapTransport(hostname, ssl=ssl, port=port,
                                    ssl_context=ssl_context, starttls=starttls)
        self.hostname = hostname
        self.username = username
        self.password = password
        self.parser_policy = policy
        self.connection = self.server.connect(username, password)
        logger.info("Connected to IMAP Server with user {username} on {hostname}{ssl}".format(
            hostname=hostname, username=username, ssl=(" over SSL" if ssl or starttls else "")))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.logout()

    def logout(self):
        self.connection.close()
        self.connection.logout()
        logger.info("Disconnected from IMAP Server {username}@{hostname}".format(
            hostname=self.hostname, username=self.username))

    def query_uids(self, **kwargs):
        query_ = build_search_query(**kwargs)
        message, data = self.connection.uid('search', None, query_)
        if data[0] is None:
            return []
        return data[0].split()

    def fetch_by_uid(self, uid):
        message, data = self.connection.uid('fetch', uid, '(BODY.PEEK[])')
        logger.debug("Fetched message for UID {}".format(int(uid)))
        raw_email = data[0][1]

        email_object = parse_email(raw_email, policy=self.parser_policy)

        return email_object

    def fetch_list(self, **kwargs):
        uid_list = self.query_uids(**kwargs)
        logger.debug("Fetch all messages for UID in {}".format(uid_list))

        for uid in uid_list:
            yield (uid, self.fetch_by_uid(uid))

    def mark_seen(self, uid):
        logger.info("Mark UID {} with \\Seen FLAG".format(int(uid)))
        self.connection.uid('STORE', uid, '+FLAGS', '(\\Seen)')

    def mark_flag(self, uid):
        logger.info("Mark UID {} with \\Flagged FLAG".format(int(uid)))
        self.connection.uid('STORE', uid, '+FLAGS', '(\\Flagged)')

    def delete(self, uid):
        logger.info("Mark UID {} with \\Deleted FLAG and expunge.".format(int(uid)))
        self.connection.expunge()

    def copy(self, uid, destination_folder):
        logger.info("Copy UID {} to {} folder".format(int(uid), str(destination_folder)))
        return self.connection.uid('COPY', uid, destination_folder)

    def move(self, uid, destination_folder):
        logger.info("Move UID {} to {} folder".format(int(uid), str(destination_folder)))
        if self.copy(uid, destination_folder):
            self.delete(uid)

    def messages(self, **kwargs):
        folder = kwargs.get('folder', False)
        msg = ""

        if folder:
            self.connection.select(folder)
            msg = " from folder '{}'".format(folder)

        logger.info("Fetch list of messages{}".format(msg))
        return self.fetch_list(**kwargs)

    def folders(self):
        return self.connection.list()
