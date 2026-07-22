from source.celery_app.celery_app import app

from source.services.email import EmailService
from source.core.logger import default_logger


@app.task
def send_message_to_email(user_email: str, msg_subject: str, msg_body: str) -> None:

    default_logger.info("Celery: Sending message with verification link to user email")
    
    email_service = EmailService()
    
    msg = email_service.prepareEmailMsg(email_receiver=user_email,
                                        message_subject=msg_subject,
                                        message_body=msg_body)
    
    email_service.sendEmail(msg)
    
    default_logger.info("Celery: Message sent")
    
    
    
    
if __name__ == "__main__":
    send_message_to_email.delay("misha162534@gmail.com", "subject1", "body2")
