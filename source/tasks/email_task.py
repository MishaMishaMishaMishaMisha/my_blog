from source.celery_app.celery_app import app
from source.services.email import EmailService
from source.core.logger import default_logger


# вариант с использованием html
@app.task
def send_html_message_to_email(user_email: str, 
                          msg_subject: str,
                          html_path: str,
                          context: dict,
                          text_content: str) -> None:

    default_logger.info("Celery: Sending html message to user email")
    
    email_service = EmailService()
    
    msg = email_service.prepareHTML_EmailMsg(email_receiver=user_email,
                                        message_subject=msg_subject,
                                        html_path=html_path,
                                        context=context,
                                        text_content=text_content)
    
    email_service.sendEmail(msg)
    
    default_logger.info("Celery: Html Message sent")


@app.task
def send_message_to_email(user_email: str, msg_subject: str, msg_body: str) -> None:

    default_logger.info("Celery: Sending message to user email")
    
    email_service = EmailService()
    
    msg = email_service.prepareEmailMsg(email_receiver=user_email,
                                        message_subject=msg_subject,
                                        message_body=msg_body)
    
    email_service.sendEmail(msg)
    
    default_logger.info("Celery: Message sent")
    
    

