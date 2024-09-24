from email import message_from_bytes, policy
from email.message import EmailMessage
from imaplib import IMAP4, IMAP4_SSL
from ssl import SSLContext


class IMAP4_Client:
    def __init__(self, host: str = "", port: int = 993, ssl_context: SSLContext = None, timeout: float = None) -> None:
        """
        IMAP4 client class over SSL connection encapsulated to simplify the outputs.

        Instantiate with: IMAP4_Client(host, port, ssl_context, timeout)

        where:
        - host: host's name (by default is localhost)
        - port: port number (by default the standard IMAP4_SSL port [ 993 ] is used)
        - ssl_context: SSLContext object that contains your certificate chain and private key (by default is None)
        - timeout: socket timeout (by default the global default socket timeout is used)
        """
        self.__host = host
        self.__port = port
        self.__sslcontext = ssl_context
        self.__timeout = timeout
        self.__imap = None

    def __enter__(self) -> 'IMAP4_Client':
        """
        Support for context management (with statement).
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Automatically disconnect when exiting the context.
        """
        self.disconnect()

    def connect(self, account: str, password: str) -> None:
        """
        Connect to the IMAP server using the provided authentication method.
        """
        # Check if it is connected.
        if self.is_logged():
            return

        try:
            # Connect to the provider's IMAP server.
            self.__imap = IMAP4_SSL(
                self.__host,
                self.__port,
                ssl_context=self.__sslcontext,
                timeout=self.__timeout
            )
            self.__imap.login(account, password)
        except (IMAP4.error, IMAP4_SSL.error) as e:
            raise ConnectionError(f"Failed to connect to IMAP server: {e}")

    def disconnect(self) -> None:
        """
        Close connection from the IMAP server if the connection is active.
        """
        # Check if it is connected.
        if not self.is_logged():
            return

        try:
            # Shutdown connection to server.
            self.__imap.logout()
        except Exception as e:
            raise RuntimeError(f"Error closing connection: {e}")

    def is_logged(self) -> bool:
        """
        Check if the client is logged in.
        """
        # Check if an IMAP instance exists.
        if self.__imap is None:
            return False

        try:
            # Send NOOP command to check connection.
            # * If less than 30 minutes have passed since the last command, the NOOP command
            # * is used to keep the connection with the IMAP server alive.
            self.__imap.noop()
            return True
        except IMAP4.error:
            return False

    def select_mailbox(self, mailbox: str = "INBOX") -> None:
        """
        Set mailbox to work with (by default used 'INBOX').
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.select(mailbox)
        except Exception as e:
            raise RuntimeError(f"Error selecting mailbox {mailbox}: {e}")

    def search_emails(self, criteria: str = "ALL") -> list[bytes]:
        """"
        Get a list of email UIDs that match the search criteria.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            status, data = self.__imap.search(None, criteria)

            if status == "OK":
                return data[0].split()

            return []
        except Exception as e:
            raise RuntimeError(f"Error searching emails: {e}")

    def fetch_emails(self, uids: str) -> list[EmailMessage]:
        """
        Fetch emails by UIDs (e.g. '120,234,330,...')  and return a list of EmailMessage objects.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            status, data = self.__imap.fetch(uids, '(RFC822)')

            if status == "OK":
                # Convert messages in EmailMessage objects
                return [message_from_bytes(message, policy=policy.default) for _, message in data[::2]]

            return []
        except Exception as e:
            raise RuntimeError(f"Error fetching email UIDs {uids}: {e}")

    def delete_emails(self, messages_uid: str) -> None:
        """
        Mark emails for deletion and permanently remove them from the mailbox.

        This method sets the '\\Deleted' flag on the specified email messages and 
        then expunges (permanently removes) those messages from the mailbox. Once 
        an email is expunged, it cannot be recovered.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.store(messages_uid, '+FLAGS', '\\Deleted')
            self.__imap.expunge()
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")

    def move_emails(self, messages_uid: str, mailbox: str) -> None:
        """
        Atomically move messages to another folder.

        Requires the MOVE capability, see :rfc:`6851`.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.store(messages_uid, '+FLAGS', f'\\{mailbox}')
            self.__imap.expunge()
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")

    def list_mailboxes(self, directory: bytes = b'""', pattern: bytes = b"*") -> list[str]:
        """
        Retrieve a list of mailboxes in the given directory with a specific pattern.

        :param directory: The directory to list mailboxes in (default is root: "").
        :param pattern: The pattern to match mailboxes (default is '*').
        :return: List of mailboxes.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            status, data = self.__imap.list(directory, pattern)

            if status == "OK":
                return [mailbox.decode().split(' "/" ')[1] for mailbox in data]

            return []
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")

    def rename_mailbox(self, old_mailbox: str, new_mailbox) -> None:
        """
        Rename mailbox named oldmailbox to newmailbox.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.rename(old_mailbox, new_mailbox)
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")

    def new_mailbox(self, mailbox: str) -> None:
        """
        Create new mailbox named 'mailbox'.
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.create(mailbox)
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")

    def delete_mailbox(self, mailbox: str) -> None:
        """
        Delete old mailbox named 'mailbox'
        """
        # Check if it is connected.
        if not self.is_logged():
            raise ConnectionError("Not connected to IMAP server")

        try:
            self.__imap.delete(mailbox)
        except Exception as e:
            raise RuntimeError(f"Error retrieving mailboxes: {e}")
