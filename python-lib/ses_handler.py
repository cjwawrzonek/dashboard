import logging
from boto.ses import SESConnection
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SESHandler(logging.Handler):
    """
    A handler class which sends an email using Amazon SES.
    """
    def __init__(self, aws_key, aws_secret, fromaddr, toaddrs, subject):
        """
        Initialize the handler.

        Initialize the instance with the AWS account key and secret, from and
        to addresses and subject line of the email.
        """
        logging.Handler.__init__(self)
        self.aws_key = aws_key
        self.aws_secret = aws_secret
        self.fromaddr = fromaddr
        if isinstance(toaddrs, basestring):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject

    def getSubject(self, record):
        """
        Determine the subject for the email.

        If you want to specify a subject line which is record-dependent,
        override this method.
        """
        return self.subject

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        client = SESConnection(self.aws_key, self.aws_secret)

        message = MIMEMultipart('alternative')
        message.set_charset('UTF-8')

        message['Subject'] = self._encode_str(self.getSubject(record))
        message['From'] = self._encode_str(self.fromaddr)
        message['To'] = self._convert_to_strings(self.toaddrs)

        from email.utils import formatdate

        body = self.format(record)
        body = "Date: {0}\r\n\r\n {1}".format(formatdate(), body)

        message.attach(MIMEText(self._encode_str(body), 'plain'))

        return client.send_raw_email(message.as_string(), self.fromaddr,
                                     destinations=self.toaddrs)

    def _convert_to_strings(self, list_of_strs):
        print(list_of_strs)
        if isinstance(list_of_strs, (list, tuple)):
            print("bah")
            print(isinstance(list_of_strs, list))
            print(isinstance(list_of_strs, tuple))
            result = ', '.join(list_of_strs)
            print(result)
        else:
            print("meh")
            result = list_of_strs
        print(result)
        return self._encode_str(result)

    def _encode_str(self, s):
        if isinstance(s, unicode):
            return s.encode('utf8')
        return s
