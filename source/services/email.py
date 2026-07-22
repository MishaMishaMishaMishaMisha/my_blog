import smtplib
from email.message import EmailMessage
from source.core.config import settings
from source.core.logger import default_logger
from source.core.exceptions import SendEmailHTMLOpeningException


class EmailService:

    def prepareEmailMsg(self, email_receiver: str, 
                        message_subject: str, 
                        message_body: str) -> EmailMessage:
    
        default_logger.debug("Preparing email message")
        msg = EmailMessage()
        msg["Subject"] = message_subject
        msg["From"] = settings.smtp.ADDRESS
        msg["To"] = email_receiver
        msg.set_content(message_body)
        
        return msg

    def prepareHTML_EmailMsg(self, email_receiver: str, 
                             message_subject: str, 
                             html_path: str) -> EmailMessage:
        
        default_logger.debug("Preparing html email message")
        msg = EmailMessage()
        msg["Subject"] = message_subject
        msg["From"] = settings.smtp.ADDRESS
        msg["To"] = email_receiver
        
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            default_logger.error(f"Prepating htmp email message: Error. {e}")
            raise SendEmailHTMLOpeningException("error while opening html file")
        else:   
            
            msg.add_alternative(html_content, subtype="hthml")
            return msg

    def sendEmail(self, msg: EmailMessage) -> None:
        
        default_logger.debug("Sending email message: trying")
        
        try:
            with smtplib.SMTP(settings.smtp.HOST, settings.smtp.PORT, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp.ADDRESS, settings.smtp.PASSWORD)
                smtp.send_message(msg)

        except smtplib.SMTPAuthenticationError:
            default_logger.error(f"Sending email: Incorrect login or password")

        except smtplib.SMTPRecipientsRefused:
            default_logger.error(f"Sending email: Recipinent refuse")

        except smtplib.SMTPServerDisconnected:
            default_logger.error(f"Sending email: server disconnected")

        except smtplib.SMTPConnectError:
            default_logger.error(f"Sending email: cant connect to smtp server")

        except smtplib.SMTPException as e:
            default_logger.error(f"Sending email: unknown smtp error {e}")

        except OSError as e:
            default_logger.error(f"Sending email: os error")
            
            
    